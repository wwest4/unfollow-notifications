"""
    =======================================================================
    unfollow-notifications

    An app that caches Twitter followers and sends a notification each time
    one unfollows.
    =======================================================================

    Copyright 2014 william.a.west@gmail.com

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import sys
import os
import tweepy
import logging
import webbrowser
import settings 

from flask import Flask
from logging.handlers import RotatingFileHandler
from settings import API_KEY,             \
                     API_SECRET,          \
                     ACCESS_TOKEN,        \
                     ACCESS_TOKEN_SECRET, \
                     CALLBACK_URL

LOG_FILE   = './log.out'

app = Flask(__name__)

def setup_logger():
    if not app.debug:
        file_handler = RotatingFileHandler(LOG_FILE,              \
                                           mode        = 'a',     \
                                           maxBytes    = 1000000, \
                                           backupCount = 0,       \
                                           encoding    = None,    \
                                           delay       = 0)
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

@app.route('/auth_setup')
def auth_setup():
    try:
        auth = tweepy.OAuthHandler(API_KEY, API_SECRET, CALLBACK_URL)
        auth_url = auth.get_authorization_url(signin_with_twitter=True)
        webbrowser.open(auth_url)
    except:
        return 'Error; problem with authentication setup.'
    return 'Authentication setup succeeded.'

# TODO
#@app.route('/auth_finish')
#def auth_finish():

if __name__ == "__main__":
    setup_logger()
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(debug=True) # turn debug off in production for security reasons
