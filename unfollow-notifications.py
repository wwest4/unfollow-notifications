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
import os
import redis
import settings 
import sys
import tweepy

from flask import (
    Flask,
    request,
    redirect,
    session,
    url_for,
    escape,
)

from settings import (
    API_KEY,
    API_SECRET,
    BASE_URL,
    LOG_FILE,
    REDIS_URL,
    SECRET_KEY,
)

app = Flask(__name__)

def setup_logger():
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler( 
            LOG_FILE,
            mode        = 'a',
            maxBytes    = 1000000,
            backupCount = 0,
            encoding    = None,
            delay       = 0
        )
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

@app.route('/')
def index():
    if 'username' in session:
        return 'home page for ' + session['username']
    else:
        return redirect(url_for('auth_setup'))

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return 'You have been logged out.'

@app.route('/auth_setup')
def auth_setup():
    try:
        auth = tweepy.OAuthHandler(
            API_KEY, 
            API_SECRET, 
            BASE_URL + '/auth_finish'
        )
        auth_url = auth.get_authorization_url(signin_with_twitter=True)
        session['request_token'] = (auth.request_token.key,
                                    auth.request_token.secret)
    except:
        return 'Error; problem with authentication setup.'
    return redirect(auth_url)

@app.route('/auth_finish')
def auth_finish():
    try:
        oauth_verifier = request.args.get('oauth_verifier', '')
    except:
        return 'Error: problem obtaining one or more request parameters.'

    try:
        auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
        (token_key, token_secret) = session['request_token']
        auth.set_request_token(token_key, token_secret)
        auth.get_access_token(oauth_verifier)
    except tweepy.TweepError:
        return 'Error! Failed to get access token.'

    api = tweepy.API(auth)
    session['username'] = api.me().screen_name
    save_access_token(auth, session['username'])
    return redirect(url_for('index'))

def save_access_token(auth, username):
    # TODO - catch exceptions & flash 
    r = redis.from_url(REDIS_URL)
    r.hset('access_token_keys', username, auth.access_token.key)
    r.hset('access_token_secrets', username, auth.access_token.secret)

if __name__ == "__main__":
    setup_logger()
    app.secret_key = SECRET_KEY
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.run(debug=True) # turn debug off in production for security reasons

# TODO - add log parameter knobs to settings.py
# TODO - stub out parameters file if missing
# TODO - add a setup route and a form to add/save settings
# TODO - convert settings to db persistence, editable via a setup route
# TODO - start writing tests
# TODO - make sure authz revocation results in a re-authz and not a fatal error

