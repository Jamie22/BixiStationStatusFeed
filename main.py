import json
import tweepy
from configparser import ConfigParser
import logging
import requests
import xml.etree.ElementTree as ElemTree
import sys

logging.basicConfig(level=logging.DEBUG)

config = ConfigParser()
config.read('config.ini')

# Get the current station status and information JSON from the BIXI API
status_req = requests.get('https://api-core.bixi.com/gbfs/en/station_status.json')
status = json.loads(status_req.text)['data']['stations']

info_req = requests.get('https://api-core.bixi.com/gbfs/en/station_information.json')
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

    for s in prev_info:
        if s['lat'] != 0 or s['lon'] != 0:
            cur = next((x for x in info if x['station_id'] == s['station_id']), None)
            tweet = ''

            if not cur:
                tweet = 'BIXI station permanently removed from '
                cur = s
            elif s['lat'] != cur['lat'] or s['lon'] != cur['lon']:
                prev_stat = next(x for x in prev_status if x['station_id'] == s['station_id'])

                if not prev_stat['is_installed']:
                    tweet = 'Upcoming '

                tweet += 'BIXI station moved from ' + s['name'] + ' to '

            if tweet:
                change = True
                places = twit_api.reverse_geocode(lat=cur['lat'], long=cur['lon'])
                place = next((x for x in places if x.place_type == "neighborhood"),
                             next(x for x in places if x.place_type == "city"))
                tweet += cur['name'] + ' http://maps.google.com/maps?q=' + str(cur['lat']) + ',' + str(cur['lon'])
                twit_api.update_status(status=tweet, place_id=place.id)

    for s in info:
        if s['lat'] != 0 or s['lon'] != 0:
            stat = next(x for x in status if x['station_id'] == s['station_id'])
            prev = next((x for x in prev_info if x['station_id'] == s['station_id']), None)
            tweet = ''

            if not prev or (prev['lat'] == 0 and prev['lon'] == 0):
                if stat['is_installed']:
                    tweet = 'New BIXI station installed at '
                else:
                    tweet = 'New BIXI station coming soon at '
            else:
                prev_stat = next(x for x in prev_status if x['station_id'] == s['station_id'])

                if stat['is_installed'] and not prev_stat['is_installed']:
                    tweet = 'BIXI station installed at '

                if not stat['is_installed'] and prev_stat['is_installed']:
                    tweet = 'BIXI station removed from '

            if tweet:
                change = True
                places = twit_api.reverse_geocode(lat=s['lat'], long=s['lon'])
                place = next((x for x in places if x.place_type == "neighborhood"),
                             next(x for x in places if x.place_type == "city"))
                tweet += s['name'] + ' http://maps.google.com/maps?q=' + str(s['lat']) + ',' + str(s['lon'])
                twit_api.update_status(status=tweet, place_id=place.id)
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
