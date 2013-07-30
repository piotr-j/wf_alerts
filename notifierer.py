from datetime import datetime as dt
import time
import sys
import re
import winsound
import ConfigParser

import logging
LOG_FILENAME = 'log.log'

# requires python-twitter
# get it here: https://github.com/bear/python-twitter
import twitter

from urllib2 import URLError

class Notifierer(object):
    def __init__(self, config):
        self._last_id = None
        self._user_last_id = {}
        self._load_config(config)

    def _load_config(self, config):
        """Try getting stuff from specified config"""
        try:
            consumer_key = config.get('TwitterSettings', 'consumer_key')
            consumer_secret = config.get('TwitterSettings', 'consumer_secret')
            access_token_key = config.get('TwitterSettings', 'access_token_key')
            access_token_secret = config.get('TwitterSettings', 'access_token_secret')

            self._update_delay = config.getint('NotifiererSettings', 'check_delay')
            self._num_tweets = config.getint('NotifiererSettings', 'num_tweets')
            self._sound = config.get('NotifiererSettings', 'sound')
            self._users = self._parse_users(config.get('MonitoredFeeds', 'users'))
            self._filters = self._parse_filters(config.get('MonitoredFeeds', 'filters'))
            self._custom_notifies = {}
        except ConfigParser.NoOptionError, e:
            print 'Please fix this config error:'
            print e
            sys.exit(1)

        self._twitter_login(consumer_key, consumer_secret, access_token_key, access_token_secret)


    def _parse_users(self, users):
        return users.split(';')   


    def _parse_filters(self, raw_filters):
        common_filters = []
        filters = {}
        raw_filters = raw_filters.split(';')
        for raw_filter in raw_filters:
            raw_filter = raw_filter.split(':')
            user = raw_filter[0]
            if user.startswith('@'):
                # filters for single user
                filters[user] = raw_filter[1].split(',')
            else:
                # filters for all users
                common_filters = raw_filter[0].split(',')

        # add common filters to user ffilters
        if common_filters:
            for user in self._users:
                filters.get(user, []).extend(common_filters)

        return filters


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
            print 'Login successful'
        except twitter.TwitterError, e:
            print 'Twitter error:', e[0][0][u'message']
            print 'Make sure you entered correct credentials!'
            raw_input()
            sys.exit(1)


    def update_feeds(self):
        """start updating all feeds periodicly"""
        while True:
            # check for new tweets
            for user in self._users:
                self._check_feed(user)
            print 'Next update in', self._update_delay, 'minutes.'
            # wait for CHECK_DELAY minutes
            time.sleep(self._update_delay * 60)

    def add_custom_notify(self, username, notify_func):
        """ add custom notify function
        it must take status text and time delta and return new notify text or None to skip"""
        self._custom_notifies[username] = notify_func

    def _check_feed(self, user):
        statuses = self._get_statuses(user, self._user_last_id.get(user, None))
        if statuses:
            # get current time for later use
            current_time = dt.now()
            # statuses are in descending order
            self._user_last_id[user] = statuses[0].id
            # check all new statuses
            filtered = []
            for status in statuses:
                filtered_status = self._check_status(status, user, current_time)
                if filtered_status:
                    filtered.append(filtered_status)
            # there are some new statuses
            if filtered:
                print 'Tweets for', user
                for filtered_status in filtered:
                    # 0 - text
                    # 1 - time delta
                    self._notify(filtered_status[0], filtered_status[1])


    def _get_statuses(self, user, since_id):
        """returns all new statuses from user since given id"""
        try:
            statuses = self._tw_api.GetUserTimeline(
                screen_name=user, 
                since_id=since_id,
                count=self._num_tweets)
            return statuses
        except twitter.TwitterError, e:
            # most likely rate limit
            print 'Twitter error:', e[0][0][u'message']
            return None


    def _check_status(self, status, user, current_time):
        """checks if given status should be displayed"""
        # calculate how long ago this tweet occured
        tweet_time = dt.fromtimestamp(status.GetCreatedAtInSeconds())
        delta_time = current_time - tweet_time
        time_delta = round(delta_time.total_seconds() / 60, 0)
        # if there is no filter just add it
        if not self._filters.get(user):
            return self._custom_notify(user, status.text, time_delta)
        # filter results
        for filter in self._filters.get(user):
            # check if desired word is in status text
            if not filter in status.text:
                continue
            #print status.text, time_delta
            return self._custom_notify(user, status.text, time_delta)
        return None


    def _custom_notify(self, user, text, time_delta):
        """parses given status text with custom user funcion"""
        # get custom notify
        custom_notify = self._custom_notifies.get(user)
        # if exists get new text
        if custom_notify:
            # custom_notify may return none it status shlound be show
            text = custom_notify(text, time_delta)
            if text:
                return text, time_delta
        else:
            return status.text, time_delta


    def _notify(self, text, time_delta):
        if not text:
            return
        print 'New tweet', str(int(time_delta)) + 'm ago!'
        print text
        self._beep(self._sound)


    def _beep(self, sound):
        try:
            # play user sound or default windows sound
            if sound:
                flags = winsound.SND_FILENAME | winsound.SND_ASYNC
                winsound.PlaySound(sound, flags)
            else:
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except RuntimeError, e:
            print 'Sound error:', e


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
    config.set('NotifiererSettings', '; path to wav sound to be played', '')
    config.set('NotifiererSettings', '; example: sound = notification.wav', '')
    config.set('NotifiererSettings', 'sound', 'notification.wav')


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
        
    raw_input()
    sys.exit(1)

# minimum amount of credits to show the alert
MIN_CREDS = 7000

def notify_wf(text, time_delta):
     # compile reged to search for alert duration in wf tweet
    regex_search = re.search('\s(\d+)[m]\s', text)
    if not regex_search:
        return None
    # theres always a credit value for the alert
    creds = int(re.search('\s(\d+)cr', text).group(1))
    # get number of minutes
    alert_duration = int(regex_search.group(1))
    time_left = int(alert_duration - time_delta)
    allowed = ['(Resource)', '(Aura)', '(Blueprint)']
    
    if time_left > 0:
        if any([x for x in allowed if x in text]) or creds > MIN_CREDS:
            return text + '\n' + str(time_left) + ' minutes left!'
    return None


if __name__ == '__main__':
    logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)
    config = _read_config()
    try:
        n = Notifierer(config)
        n.add_custom_notify('@WarframeAlerts', notify_wf)
        n.update_feeds()
    except KeyboardInterrupt, e:
        print 'Good bye.'
    except URLError, e:
        print 'Url error, see log for details'
        logging.exception('There was a problem with the connection:')
        raw_input('Enter to quit')
    except Exception, e:
        print 'Unknown error, see log for details'
        logging.exception('Unknown error:')
        raw_input('Enter to quit')

        