import logging

import azure.functions as func
import twitter 
import traceback
import os

def _envRead(key):
    return os.environ[key]

def main(req: func.HttpRequest) -> func.HttpResponse:
    charLimit = 230
    consumer_key        = _envRead('consumer_key')
    consumer_secret     = _envRead('consumer_secret')
    access_token        = _envRead('access_token')
    access_token_secret = _envRead('access_token_secret')    

    try:    
        if req.method == "GET": 
            return func.HttpResponse("It works.",status_code=200)
        
        twitterClient = twitter.Api(consumer_key,
                        consumer_secret,
                        access_token,
                        access_token_secret)
        
        # logging.info("Credential verification: {}".format(twitterClient.VerifyCredentials()))
        jsonEvent = req.get_json()
        if jsonEvent:
            logging.info(jsonEvent)
            if 'Created Migration' in jsonEvent['message']:
                vmname = jsonEvent['involvedObject']['name']
                message = jsonEvent['lastTimestamp'] + ' : ' + "Virtual Machine %s migrated!!!" % vmname
                message = (message[:charLimit-3] + "...") if len(message) > charLimit else message
                twitterClient.PostUpdate(message)
            return func.HttpResponse("Posted.",status_code=200)
        else:
            raise Exception("No content to post or unknown error for request: {}".format(req))
    except Exception as e:
        message = "Error processing event or posting update.\nMessage: {}".format(e)
        traceback.print_exc()
        logging.error(message)
        return func.HttpResponse(
                message,
                status_code=400
            )
