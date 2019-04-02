import logging

import azure.functions as func
# import twitter 
import os

def _envRead(key):
    return os.environ[key]

def main(req: func.HttpRequest) -> func.HttpResponse:
    consumer_key        = _envRead('consumer_key')
    consumer_secret     = _envRead('consumer_secret')
    access_token        = _envRead('access_token')
    access_token_secret = _envRead('access_token_secret')

    try:    
        # twitterClient = twitter.Api(consumer_key,
        #                 consumer_secret,
        #                 access_token,
        #                 access_token_secret)

        # # replace with post call twitterClient.postUpdate(req.get_json())
        # logging.info(twitterClient.VerifyCredentials())
        logging.info(f"Received CloudEvent: {req.get_json()}")
        return func.HttpResponse("Posted!",status_code=200)
    except:
        return func.HttpResponse(
                "Error processing event or posting update!",
                status_code=400
            )
    
    
    
    
