#!/usr/bin/env python
'''
=======================================================================
unfollow-notifications

An app that caches Twitter followers and sends a notification each time
unfollows are detected.
=======================================================================

Copyright 2014-2017 william.a.west@gmail.com

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import json
import os
from base64 import b64decode

import boto3
import twitter

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN_KEY = os.environ.get('ACCESS_TOKEN_KEY')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')

if os.environ.get('LAMBDA_DECRYPT', 'False') == 'True':
    CONSUMER_KEY = boto3.client('kms').\
        decrypt(CiphertextBlob=b64decode(CONSUMER_KEY))['Plaintext']
    CONSUMER_SECRET = boto3.client('kms').\
        decrypt(CiphertextBlob=b64decode(CONSUMER_SECRET))['Plaintext']
    ACCESS_TOKEN_KEY = boto3.client('kms').\
        decrypt(CiphertextBlob=b64decode(ACCESS_TOKEN_KEY))['Plaintext']
    ACCESS_TOKEN_SECRET = boto3.client('kms').\
        decrypt(CiphertextBlob=b64decode(ACCESS_TOKEN_SECRET))['Plaintext']

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
TABLE_NAME = os.environ.get('TABLE_NAME', 'unfollow-notifications')
QUEUE_NAME = os.environ.get('QUEUE_NAME', 'unfollow-notifications')


class Cache(object):
    '''a place to store the last known followers list

    Methods:
       update(all_follower=(dict),adds=(set),deletes=(set)) - update cache
       get_followers() - pull all followers from cache
    '''
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        self.table = self.dynamodb.Table(TABLE_NAME)

    def update(self, all_followers=None, adds=None, deletes=None):
        '''performe a differential update of the cache

        given lists of ids to add and delete, and a list of all
        known followers (cached and current), update the cached
        by adding and deleting the appropriate records

        Arguments:
           all_followers - a merged dict of known followers keyed by id
           adds - a set of follower ids to add
           deletes - a set of follower ids to delete
        '''
        # limit write set to new followers since last cache
        with self.table.batch_writer() as batch:
            for follower in adds:
                record = {}
                record['id'] = int(follower)
                record.update(all_followers[follower])
                batch.put_item(Item=record)

            for follower in deletes:
                batch.delete_item(Key={'id': int(follower)})

    def get_followers(self):
        '''get all followers from the cache

        this uses a scan(), which is totally fine even for a
        minimally provisioned dynamodb instance because
        only one client should be using the cache. if for some
        reason this gets scaled, bump the provisioning ($) or
        switch this from dynamodb to blob storage

        returns a dict of followers keyed by id (stringified)
        '''
        records = self.table.scan()['Items']
        results = {}
        for record in records:
            results[str(record['id'])] = {
                'name': record['name'],
                'screen_name': record['screen_name']
            }
        return results


class Notifier(object):
    '''check twitter followers, compary against cache, notify if unfollows seen

    Arguments:
       event - lambda trigger event object
       context - trigger event context data
    '''

    def __init__(self, event=None, context=None):
        self.event = event
        self.context = context

        self.cached_followers = None
        self.current_followers = None

        self.unfollowers = None
        self.new_follows = None

    def run(self):
        '''runtime entry point for the class

        use this method to kick off the notifier
        '''
        cache = Cache()

        self.current_followers = self.get_followers()
        self.cached_followers = cache.get_followers()

        self.unfollowers = self.get_unfollowers()
        self.new_follows = self.get_new_follows()

        print json.dumps({
            'current': len(self.current_followers),
            'cached': len(self.cached_followers),
            'follows': len(self.new_follows),
            'unfollows': len(self.unfollowers),
        })

        self.notify_unfollows()

        merged_followers = self.cached_followers.copy()
        merged_followers.update(self.current_followers)

        cache.update(
            all_followers=merged_followers,
            adds=self.new_follows,
            deletes=self.unfollowers
        )

    def get_unfollowers(self):
        '''calculate unfollowers based on known cache and current list

        returns a set of followers
        '''
        cached_ids = set(self.cached_followers.keys())
        current_ids = set(self.current_followers.keys())
        return cached_ids - current_ids

    def get_new_follows(self):
        '''calculate new followers based on known cache and current list

        returns a set of followers
        '''
        cached_ids = set(self.cached_followers.keys())
        current_ids = set(self.current_followers.keys())
        return current_ids - cached_ids

    def trim_follower(self, follower):
        '''helper method for extracting fields from twitter API return object
        '''
        return {
            'name': follower.name,
            'screen_name': follower.screen_name
        }

    def get_followers(self):
        '''get current followers via the twitter API

        returns a hash of followers keyed by id (stringified)
        '''
        api = twitter.Api(
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token_key=ACCESS_TOKEN_KEY,
            access_token_secret=ACCESS_TOKEN_SECRET
        )
        return {str(f.id): self.trim_follower(f) for f in api.GetFollowers()}

    def notify_unfollows(self):
        '''send a notification when unfollowers are detected
        '''
        count = len(self.unfollowers)
        if count == 0:
            return

        sqs = boto3.resource('sqs', region_name=AWS_REGION)
        queue = sqs.get_queue_by_name(QueueName=QUEUE_NAME)
        unfollowers = [self.cached_followers[fid] for fid in self.unfollowers]

        queue.send_message(MessageBody=json.dumps({
            'count': count,
            'summary': 'unfollow activity detected',
            'unfollowers': unfollowers
        }))


def entry(event, context):
    '''use as entry point for aws lambda

    Arguments:
       event - triggering event
       context - runtime context
    '''
    notifier = Notifier(event, context)
    notifier.run()


if __name__ == '__main__':
    entry(None, None)
