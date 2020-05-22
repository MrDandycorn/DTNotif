import requests
import json
import time
from credentials import vk_personal_token, vk_stream_bot_token, vk_stream_bot_owner_id, vk_broadcast_token, vk_broadcast_id, vk_dev_broadcast_id, twitch_client, \
    streamer_ids, vk_test_bot_owner_id, dev, twitch_token
from os import path
from random import getrandbits

uptimes = [0.0] * len(streamer_ids)
flags = [False] * len(streamer_ids) if dev else [True] * len(streamer_ids)
timeout = [0] * len(streamer_ids)
broadcast_id = vk_dev_broadcast_id if dev else vk_broadcast_id
owner_id = vk_test_bot_owner_id if dev else vk_stream_bot_owner_id


def make_vk_post(name, game):
    payload = {'owner_id': owner_id,
               'access_token': vk_personal_token,
               'v': '5.103',
               'from_group': '1',
               'message': f'{name} сейчас стримит {game} на https://twitch.tv/{name.lower()}',
               'attachments': 'https://twitch.tv/' + name.lower()}
    vk_post = requests.get('https://api.vk.com/method/wall.post', params=payload).json()
    post_id = vk_post['response']['post_id']
    data = {'message': {'attachment': f'wall{owner_id}_{post_id}'}}
    headers = {'content-type': 'application/json'}
    broadcast_params = {
        'token': vk_broadcast_token,
        'list_ids': broadcast_id,
        'run_now': 1
    }
    requests.post('https://broadcast.vkforms.ru/api/v2/broadcast', params=broadcast_params, data=json.dumps(data), headers=headers)


def post_start_time(start_time, user_id, user_num):
    uptimes[user_num] = start_time
    with open(path.join('uptimes', f'{user_id}.txt'), 'w+') as uptime:
        uptime.write(str(start_time))


def send_uptime(user_id, start_time):
    uptime = time.time() - start_time - 300
    formatted = time.strftime("%H:%M:%S", time.gmtime(uptime))
    payload = {'access_token': vk_stream_bot_token,
               'v': '5.103',
               'message': f'{get_username(user_id)} стримил {formatted}',
               'chat_id': 1,
               'random_id': getrandbits(64)}
    requests.get('https://api.vk.com/method/messages.send', params=payload)


def get_username(user_id):
    headers = {'Authorization': 'Bearer ' + twitch_token, 'Client-ID': twitch_client}
    params = {'id': user_id}
    response = requests.get('https://api.twitch.tv/helix/users', params=params, headers=headers).json()
    return response['data'][0]['display_name']


def twitch_request():
    url = 'https://api.twitch.tv/helix/streams?user_id' + '&user_id='.join(streamer_ids)
    headers = {'Authorization': 'Bearer ' + twitch_token, 'Client-ID': twitch_client}
    res = requests.get(url, headers=headers).json()['data']
    info = {}
    for stream in res:
        info[stream['user_id']] = stream
    for i, streamer in enumerate(streamer_ids):
        print(streamer)
        try:
            streamer_info = info.get(streamer)
            if streamer_info:
                print('User ' + streamer + ' is streaming')
                if uptimes[i] == 0:
                    uptime_temp = open(path.join('uptimes', f'{streamer}.txt'), 'r')
                    uptimes[i] = float(uptime_temp.read())
                    uptime_temp.close()
                    if uptimes[i] != 0:
                        print('Set ' + streamer + ' uptime to ' + time.strftime("%H:%M:%S", time.gmtime(time.time() - uptimes[i])))
                if not flags[i]:
                    if timeout[i] != 0:
                        print(streamer + ' resumed streaming')
                        timeout[i] = 0
                        flags[i] = True
                    else:
                        streamer_info = streamer_info[0]
                        name = get_username(streamer)
                        print(name + ' started streaming')
                        gameid = streamer_info.get('game_id')
                        try:
                            game = requests.get('https://api.twitch.tv/helix/games?id=' + gameid, headers=headers).json()['data'][0]['name']
                        except (IndexError, KeyError):
                            game = ''
                        make_vk_post(name, game)
                        flags[i] = True
                        post_start_time(time.time(), streamer, i)
            elif not streamer_info and flags[i]:
                flags[i] = False
                print(f'User {streamer} stopped streaming')
                timeout[i] = 1
            else:
                print(f'User {streamer} is not streaming')
                if timeout[i] != 0:
                    if timeout[i] > 5:
                        timeout[i] = 0
                        if uptimes[i] != 0:
                            print(send_uptime(streamer, uptimes[i]))
                    else:
                        timeout[i] += 1
                else:
                    post_start_time(0, streamer, i)
        except Exception as r:
            print('Error: ' + str(r))


while True:
    twitch_request()
    time.sleep(60)
