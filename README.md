# WF Alerts

**Simple notifier for [WarframeAlerts](https://twitter.com/WarframeAlerts) tweets**

Author: Piotr Jastrzebski <piotrj.dev@gmail.com>

## Introduction

This script notifies about alerts containing specific keywords. While its meant for Warframe Alerts tweets, it can be used for other users as well. Currently it works only on windows, as it requires `winsound` for notification sound.

## How to setup and run

Get the code and install requirements:
```
 $ git clone git://github.com/piotr-j/wf_alerts.git
 $ cd wf_alerts
 $ pip install -r requirements.txt
```

Run the script once, this will generate config file.
```
 $ notifierer.py
```

Fill out the config file. You need some .wav file for notification sound. Due to recent twitter api changes you also need to generate new app keys at [Twitter console](https://dev.twitter.com/apps/new). 

Run the script again, if all is setup correctly it will play a sound when interesting alert comes up.
```
 $ notifierer.py
```