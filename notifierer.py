from datetime import datetime as dt
import time
import sys
import re
import ConfigParser
# requires python-twitter
# get it here: https://github.com/bear/python-twitter
import twitter

# username of user you want to check eg. @WarframeAlerts
USERS = ['@WarframeAlerts', '@Totalbiscuit']
# what must be in message to be notified
FILTERS = ['(Blueprint)', '(Artifact)']
REGEX_FILTERS = ['']

class Notifierer(object):
    def __init__(self, config):
        self._last_id = None
        self._user_last_id = {}
        self._load_config()
        self._update_feeds()


    def _load_config(self):
        """Try getting stuff from read config"""
        try:
            consumer_key = config.get('TwitterSettings', 'consumer_key')
            consumer_secret = config.get('TwitterSettings', 'consumer_secret')
            access_token_key = config.get('TwitterSettings', 'access_token_key')
            access_token_secret = config.get('TwitterSettings', 'access_token_secret')

            self._update_delay = config.getint('NotifiererSettings', 'check_delay')
            self._num_tweets = config.getint('NotifiererSettings', 'num_tweets')

            self._users = self._parse_users(config.get('MonitoredFeeds', 'users'))
            self._filters = self._parse_filters(config.get('MonitoredFeeds', 'filters'))
        except ConfigParser.NoOptionError, e:
            print 'Please fix this config error:'
            print e
            sys.exit(1)

        self._twitter_login(consumer_key, consumer_secret, access_token_key, access_token_secret)


    def _twitter_login(self, consumer_key, consumer_secret, access_token_key, access_token_secret):
        """login to twitter with given data"""
        self._tw_api = twitter.Api(
                    consumer_key=consumer_key,
                    consumer_secret=consumer_secret,
                    access_token_key=access_token_key,
                    access_token_secret=access_token_secret)
        try:
            # veryfy as its not checked above
            self._tw_api.VerifyCredentials()
        except twitter.TwitterError, e:
            print 'Twitter error:', e[0][0][u'message']
            sys.exit(1)


    def _update_feeds(self):
        """update all feeds periodicly"""
        while True:
            # check for new tweets
            for user in self._users:
                self._check_feed(user)
            print 'Next update in', self._update_delay, 'minutes.'
            # wait for CHECK_DELAY minutes
            time.sleep(self._update_delay * 60)


    def _parse_users(self, users):
        return users.split(';')   


    def _parse_filters(self, raw_filters):
        filters = {}
        raw_filters = raw_filters.split(';')
        for raw_filter in raw_filters:
            raw_filter = raw_filter.split(':')
            user = raw_filter[0]
            if(len(raw_filter) == 2):
                user_filters = raw_filter[1].split(',')

            filters[user] = user_filters

        print filters
        return filters
    

    def _check_feed(self, user):
        statuses = self._get_statuses(user)
        if statuses:
            # get current time for later use
            current_time = dt.now()
            # statuses are in descending order
            self._user_last_id[user] = statuses[0].id
            print 'Tweets for', user
            # check all new statuses
            for status in statuses:
                self._check_status(status, user, current_time)


    def _get_statuses(self, user):
        try:
            statuses = self._tw_api.GetUserTimeline(
                screen_name=user, 
                since_id=self._user_last_id.get(user, None),
                count=self._num_tweets)
            return statuses
        except twitter.TwitterError, e:
            # most likely rate limit
            print 'Twitter error:', e[0][0][u'message']
            return None


    def _check_status(self, status, user, current_time):
        # calculate how long ago this tweet occured
        tweet_time = dt.fromtimestamp(status.GetCreatedAtInSeconds())
        delta_time = current_time - tweet_time
        time = round(delta_time.total_seconds() / 60, 0)

        if(self._filters.get(user)):
            for filter in self._filters.get(user):
                if not filter in status.text:
                    continue
                self._notify(status.text, time)
        else:
            self._notify(status.text, time)


    def _notify(self, text, time):
        print text


def _read_config():
    config = ConfigParser.SafeConfigParser()
    config.read('notifierer.cfg')
    if config.sections() == []:
        _create_config()
    else:
        return config

def _create_config():
    print """No config file found, creating new one. Please fill it in. """
    # write defualt config
    config = ConfigParser.SafeConfigParser()

    config.add_section('TwitterSettings')
    config.set('TwitterSettings', '; You need to create new application api for twitter here:', '')
    config.set('TwitterSettings', '; https://dev.twitter.com/apps/new', '')
    config.set('TwitterSettings', '; more info: https://dev.twitter.com/discussions/631', '')
    config.set('TwitterSettings', '; and fill this:', '')
    config.set('TwitterSettings', 'consumer_key', 'your_consumer_key_goes_here')
    config.set('TwitterSettings', 'consumer_secret', 'your_consumer_secret_goes_here')
    config.set('TwitterSettings', 'access_token_key', 'your_access_token_key_goes_here')
    config.set('TwitterSettings', 'access_token_secret', 'your_access_token_secret_goes_here')

    config.add_section('NotifiererSettings')
    config.set('NotifiererSettings', '; time in minutes between updates', '')
    config.set('NotifiererSettings', '; small delay and large amount of feeds will cause rate limit issues', '')
    config.set('NotifiererSettings', 'check_delay', '5')
    config.set('NotifiererSettings', '; max number of tweets per update, max 200. default: 20', '')
    config.set('NotifiererSettings', 'num_tweets', '20')

    config.add_section('MonitoredFeeds')
    config.set('MonitoredFeeds', '; add usernames to monitor, semicolon (;) separated', '')
    config.set('MonitoredFeeds', '; example: users', '@WarframeAlerts')
    config.set('MonitoredFeeds', 'users', '@WarframeAlerts')
    config.set('MonitoredFeeds', '; add filters to be aplied, semicolon (;) separated', '')
    config.set('MonitoredFeeds', '; if no filters are specified for given username, all tweets will apear', '')
    config.set('MonitoredFeeds', '; names must be exact', '')
    config.set('MonitoredFeeds', '; example: filters', '@WarframeAlerts:(Blueprint),(Artifact);...')
    config.set('MonitoredFeeds', 'filters', '@WarframeAlerts:(Blueprint),(Artifact)')

    # Write it'
    with open('notifierer.cfg', 'w') as configfile:
        config.write(configfile)   

    sys.exit(1)

if __name__ == '__main__':
    config = _read_config()
    try:
        Notifierer(config)
    except KeyboardInterrupt, e:
        print 'Good bye.'

