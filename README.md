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

The sample code to send _cloudevents_ to a Twitter feed is on `http-trigger/__init__.py`

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
There is a `twitter.yaml` file that should be updated with proper values.  Once you update the file you can create the secrets using:

`kubectl apply -n azure-functions  -f twitter.yaml`

 Remember to encode those values in base64. For example: `echo -n 'VALUE' | base64
VkFMVUU=`  

* We need to add the secrets to the service specification.  The easiest way to do that is to apply a patch as follows: 

  ```
  kubectl patch ksvc/http-trigger -n azure-functions --type json --patch "$(cat env_patch.json)"
  service.serving.knative.dev/http-trigger patched
  ```

This patch will generate a new Revision in the Knative service since we are modifying the configuration of the application. 

* Ensure the function is up and returns a 200
  
  `curl -v -H "Host: httptrigger.azure-functions.example.com" http://$(minikube ip):31380/api/http-trigger`

* Simulating POSTing an empty CloudEvent to it
  
  `curl -d "{}" -H "Content-Type: application/json" -H "Host: httptrigger.azure-functions.example.com" http://$(minikube ip):31380/api/http-trigger`

* Check out the function logs
  
  `kubectl logs -n azure-functions -l serving.knative.dev/service=httptrigger -c user-container`


## Knative Event Source Setup 

### Create a ServiceAccount with permissions to watch k8s events

`kubectl apply -f eventing/serviceAccount.yaml`

### Create a Knative Eventing Channel

`kubectl apply -f eventing/channel.yaml`

### Create a KubernetesEventSource

`kubectl apply -f eventing/k8sEventSource.yaml`

### Create a Subscription pointing to our Azure Function

`kubectl apply -f eventing/subscription.yaml`

# Sending event 

* Create a Kubernetes event to confirm things work
  `kubectl run -n default -i --tty busybox --image=busybox --restart=Never --rm=true -- sh`

Just exit the container after it starts by typing `exit`

* Check the Twitter feed or container logs using: 

  `kubectl logs -n azure-functions -l serving.knative.dev/service=httptrigger -c user-container`

You should see something like:
  ```
  info: Function.http-trigger[0]
        Executed 'Functions.http-trigger' (Succeeded, Id=4f07df31-a12c-4acd-9ede-297887fb38f7)
  info: Function.http-trigger[0]
        Executing 'Functions.http-trigger' (Reason='This function was programmatically called via the host APIs.', Id=4b20130f-0869-4a16-aff1-11da9a447dbd)
  info: Function.http-trigger.User[0]
        {'metadata': {'name': 'busybox.158e659be89c8e31', 'namespace': 'default', 'selfLink': '/api/v1/namespaces/default/events/busybox.158e659be89c8e31', 'uid': 'acdf5462-4cea-11e9-93fd-307a181b66b4', 'resourceVersion': '31059', 'creationTimestamp': '2019-03-22T21:37:21Z'}, 'involvedObject': {'kind': 'Pod', 'namespace': 'default', 'name': 'busybox', 'uid': '955d19f5-4cea-11e9-93fd-307a181b66b4', 'apiVersion': 'v1', 'resourceVersion': '30978', 'fieldPath': 'spec.containers{busybox}'}, 'reason': 'Killing', 'message': 'Killing container with id docker://busybox:Need to kill Pod', 'source': {'component': 'kubelet', 'host': 'minikube'}, 'firstTimestamp': '2019-03-22T21:37:21Z', 'lastTimestamp': '2019-03-22T21:37:21Z', 'count': 1, 'type': 'Normal', 'eventTime': None, 'reportingComponent': '', 'reportingInstance': ''}
  info: Function.http-trigger[0]
        Executed 'Functions.http-trigger' (Succeeded, Id=4b20130f-0869-4a16-aff1-11da9a447dbd)
  ```

![Twitter feed](https://raw.githubusercontent.com/markito/ktweeter/master/screenshot.png)

# Troubleshooting

* Status is a duplicate.

When monitoring the logs if you see the following message: 
```
Error processing event or posting update.
      Message: [{'code': 187, 'message': 'Status is a duplicate.'}]
```
That's because Twitter's API don't allow for duplicate messages within a certain period of time.  


