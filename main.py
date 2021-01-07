import json
import tweepy
from configparser import ConfigParser
import logging
import requests
import xml.etree.ElementTree as ElemTree
import sys
import geopy.distance

logging.basicConfig(level=logging.DEBUG)

config = ConfigParser()
config.read('config.ini')

# Get the current station status and information JSON from the BIXI API
status_req = requests.get('https://gbfs.velobixi.com/gbfs/en/station_status.json')
status = json.loads(status_req.text)['data']['stations']

info_req = requests.get('https://gbfs.velobixi.com/gbfs/en/station_information.json')
info = json.loads(info_req.text)['data']['stations']

# Retrieve the previous station status and information JSON from Pastebin
r = requests.post("https://pastebin.com/api/api_post.php",
                  data={'api_dev_key': config.get('pastebin', 'dev_key'),
                        'api_user_key': config.get('pastebin', 'user_key'),
                        'api_option': 'list',
                        'api_results_limit': 1000})

if "Bad API request" in r.text:
    logging.error(r.text)
    sys.exit(r.text)

# Parse the XML that is returned
pastes = ElemTree.fromstring('<pastes>' + r.text + '</pastes>')
prev_data = pastes.findall("paste[paste_title = 'bixi']")
change = False

if prev_data:
    prev_data_req = requests.get('https://pastebin.com/raw/' + prev_data[-1].find('paste_key').text)
    prev_obj = json.loads(prev_data_req.text)
    prev_status = prev_obj['status']
    prev_info = prev_obj['info']

    auth = tweepy.OAuthHandler(
        config.get('twitter', 'consumer_key'),
        config.get('twitter', 'consumer_secret')
    )

    auth.set_access_token(
        config.get('twitter', 'access_token'),
        config.get('twitter', 'access_token_secret')
    )

    twit_api = tweepy.API(auth)
    tweets = []

    for prev in prev_info:
        if prev['lat'] != 0 or prev['lon'] != 0:
            s = next((x for x in info if x['station_id'] == prev['station_id']), None)

            if not s:
                tweets.append(('BIXI station permanently removed from ', prev))

    for s in info:
        if s['lat'] != 0 or s['lon'] != 0:
            stat = next(x for x in status if x['station_id'] == s['station_id'])
            prev = next((x for x in prev_info if x['station_id'] == s['station_id']), None)

            if not prev or (prev['lat'] == 0 and prev['lon'] == 0):
                if stat['is_installed']:
                    tweets.append(('New BIXI station installed at ', s))
                else:
                    tweets.append(('New BIXI station coming soon at ', s))
            else:
                prev_stat = next(x for x in prev_status if x['station_id'] == s['station_id'])

                if not stat['is_installed'] and prev_stat['is_installed']:
                    tweets.append(('BIXI station removed from ', prev))

                if prev['lat'] != s['lat'] or prev['lon'] != s['lon']:
                    tweet = ''
                    if not stat['is_installed'] or not prev_stat['is_installed']:
                        tweet = 'Upcoming '

                    dist = geopy.distance.distance((prev['lat'], prev['lon']), (s['lat'], s['lon'])).m

                    if dist < 1000:
                        str_dist = str(round(dist)) + ' m'
                    else:
                        str_dist = str(round(dist / 1000)) + ' km'

                    tweet += 'BIXI station moved ' + str_dist + ' from ' + prev['name'] + ' to '
                    tweets.append((tweet, s))

                if stat['is_installed'] and not prev_stat['is_installed']:
                    tweets.append(('BIXI station installed at ', s))

    for t, s in tweets:
        change = True
        places = twit_api.reverse_geocode(lat=s['lat'], long=s['lon'])
        place = next((x for x in places if x.place_type == "neighborhood"),
                     next(x for x in places if x.place_type == "city"))
        t += s['name'] + ' http://maps.google.com/maps?q=' + str(s['lat']) + ',' + str(s['lon'])
        twit_api.update_status(status=t, place_id=place.id)
else:
    change = True

if change:
    # Keep only the attributes needed for storage
    info = [{"station_id": s['station_id'], "name": s['name'], "lat": s['lat'], "lon": s['lon']} for s in info]
    status = [{"station_id": s['station_id'], "is_installed": s['is_installed']} for s in status]

    r = requests.post("https://pastebin.com/api/api_post.php",
                      data={'api_dev_key': config.get('pastebin', 'dev_key'),
                            'api_user_key': config.get('pastebin', 'user_key'),
                            'api_option': 'paste',
                            'api_paste_name': 'bixi',
                            'api_paste_expire_date': '1W',
                            'api_paste_code': json.dumps({"info": info, "status": status})})

    if "Bad API request" in r.text:
        logging.error(r.text)
