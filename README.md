# ktweeter 🔊
An example of an Azure Function that can post K8s events to a Twitter feed running in Kubernetes and using Knative.

## Setup

### Prerequisites:
- Download Azure Functions CLI `func`.  https://github.com/Azure/azure-functions-core-tools/releases
- Python 3.6
- Setup OpenShift/Kubernetes as described below with Knative.

#### On OpenShift 

Make sure you have a cluster Knative installed.  Instructions here...

#### On Minikube

Follow the instructions here to setup Minikube and Knative. https://redhat-developer-demos.github.io/knative-tutorial/knative-tutorial/v1.0.0/setup.html#kubernetes-cluster


## Create a function project 

For detailed information about how to create Python Functions in Azure Functions follow this guide: 
https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-python


* Create a new python function app

  `func init --worker-runtime python --docker`

* Create a http-triggered function

  `func new --template 'HTTP trigger' --name http-trigger`

* Enable function logging to console
  ```
  cat <<EOF > host.json
  {
      "version":  "2.0",
      "logging": {
          "console": {
              "isEnabled": "true"
          },
          "logLevel": {
              "default": "Information"
          }
      },
  }
  ```
* Disable auth for our http trigger

  `sed -i -e 's/"authLevel": "function"/"authLevel": "anonymous"/' http-trigger/function.json`

* Update the function code to log CloudEvents
  ```
  cat <<EOF > http-trigger/__init__.py
  import logging
  import azure.functions as func

  def main(req: func.HttpRequest) -> func.HttpResponse:
      try:
          logging.info(f"Received CloudEvent: {req.get_json()}")
      except ValueError:
          logging.info('Ready to receive CloudEvents!')
      return func.HttpResponse(status_code=200)
  EOF
  ```

## Deploy 

* Set container registry 

  `export REGISTRY=docker.io/markito`

* Update the Dockerfile - Add the following line right after `FROM`

  `ENV ASPNETCORE_URLS=http://+:8080`

* Deploy the function to Knative
  
  `func deploy --platform knative --name http-trigger --registry $REGISTRY --config ~/.kube/config`

* Deploy the secret file with your Twitter API token and keys

For example: 
  ```
  apiVersion: v1
  kind: Secret
  metadata:
    name: twitter.creds
  type: Opaque
  data:
    consumer_key: YWNjZXNzX3Rva2VuX3NlY3JldA==
    consumer_secret: YWNjZXNzX3Rva2VuX3NlY3JldA==
    access_token: YWNjZXNzX3Rva2VuX3NlY3JldA==
    access_token_secret: YWNjZXNzX3Rva2VuX3NlY3JldA==
  ```

* Remember to encode those values in base64. For example: `echo -n 'VALUE' | base64
VkFMVUU=` 


* Ensure the function is up and returns a 200
  
  `curl -v -H "Host: httptrigger.azure-functions.example.com" http://$(minikube ip):31380/api/http-trigger`

* Simulating POSTing an empty CloudEvent to it
  
  `curl -d "{}" -H "Content-Type: application/json" -H "Host: httptrigger.azure-functions.example.com" http://$(minikube ip):31380/api/http-trigger`

* Check out the function logs
  
  `kubectl logs -n azure-functions -l serving.knative.dev/service=httptrigger -c user-container`

## Knative Event Source Setup 

### Create a ServiceAccount with permissions to watch k8s events
  ```
  cat <<EOF | kubectl create -f -
  apiVersion: v1
  kind: ServiceAccount
  metadata:
    name: events-sa
    namespace: default
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: Role
  metadata:
    creationTimestamp: null
    name: event-watcher
  rules:
  - apiGroups:
    - ""
    resources:
    - events
    verbs:
    - get
    - list
    - watch
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: RoleBinding
  metadata:
    creationTimestamp: null
    name: k8s-ra-event-watcher
  roleRef:
    apiGroup: rbac.authorization.k8s.io
    kind: Role
    name: event-watcher
  subjects:
  - kind: ServiceAccount
    name: events-sa
    namespace: default
  EOF
  ```

### Create a Knative Eventing Channel
  ```
  cat <<EOF | kubectl create -n default -f -
  apiVersion: eventing.knative.dev/v1alpha1
  kind: Channel
  metadata:
    name: testchannel
  spec:
    provisioner:
      apiVersion: eventing.knative.dev/v1alpha1
      kind: ClusterChannelProvisioner
      name: in-memory-channel
  EOF
  ```


### Create a KubernetesEventSource
  ```
  cat <<EOF | kubectl create -n default -f -
  apiVersion: sources.eventing.knative.dev/v1alpha1
  kind: KubernetesEventSource
  metadata:
    name: testevents
  spec:
    namespace: default
    serviceAccountName: events-sa
    sink:
      apiVersion: eventing.knative.dev/v1alpha1
      kind: Channel
      name: testchannel
  EOF
  ```

### Create a Subscription pointing to our Azure Function
  ```
  cat <<EOF | kubectl create -n default -f -
  apiVersion: eventing.knative.dev/v1alpha1
  kind: Subscription
  metadata:
    name: testevents-subscription
  spec:
    channel:
      apiVersion: eventing.knative.dev/v1alpha1
      kind: Channel
      name: testchannel
    subscriber:
      dnsName: http://httptrigger.azure-functions.svc.cluster.local/api/http-trigger
  EOF
  ```

# Sending event 

* Create a Kubernetes event to confirm things work
  `kubectl run -n default -i --tty busybox --image=busybox --restart=Never --rm=true -- sh`

Just exit the container after it starts by typing `exit`

* Check out the function logs
  `kubectl logs -n azure-functions -l serving.knative.dev/service=httptrigger -c user-container`

Should see something like:
  ```
  info: Function.http-trigger[0]
        Executed 'Functions.http-trigger' (Succeeded, Id=4f07df31-a12c-4acd-9ede-297887fb38f7)
  info: Function.http-trigger[0]
        Executing 'Functions.http-trigger' (Reason='This function was programmatically called via the host APIs.', Id=4b20130f-0869-4a16-aff1-11da9a447dbd)
  info: Function.http-trigger.User[0]
        Received CloudEvent: {'metadata': {'name': 'busybox.158e659be89c8e31', 'namespace': 'default', 'selfLink': '/api/v1/namespaces/default/events/busybox.158e659be89c8e31', 'uid': 'acdf5462-4cea-11e9-93fd-307a181b66b4', 'resourceVersion': '31059', 'creationTimestamp': '2019-03-22T21:37:21Z'}, 'involvedObject': {'kind': 'Pod', 'namespace': 'default', 'name': 'busybox', 'uid': '955d19f5-4cea-11e9-93fd-307a181b66b4', 'apiVersion': 'v1', 'resourceVersion': '30978', 'fieldPath': 'spec.containers{busybox}'}, 'reason': 'Killing', 'message': 'Killing container with id docker://busybox:Need to kill Pod', 'source': {'component': 'kubelet', 'host': 'minikube'}, 'firstTimestamp': '2019-03-22T21:37:21Z', 'lastTimestamp': '2019-03-22T21:37:21Z', 'count': 1, 'type': 'Normal', 'eventTime': None, 'reportingComponent': '', 'reportingInstance': ''}
  info: Function.http-trigger[0]
        Executed 'Functions.http-trigger' (Succeeded, Id=4b20130f-0869-4a16-aff1-11da9a447dbd)
  ```

# Troubleshooting


