import requests
import json
import time
from credentials import vkPersKey, vkStreamBotKey, vkStreamOwnerID, twitchKeyToken, vkBroadcastToken, vkWorkBroadcastID, twitchClient, streamerIds,\
    vkTestBroadcastID, vkTestOwnerID, dev, twitchToken
from os import path
from random import getrandbits

uptimes = [0.0] * len(streamerIds)
flags = [False] * len(streamerIds) if dev else [True] * len(streamerIds)
timeout = [0] * len(streamerIds)
broadcast_id = vkTestBroadcastID if dev else vkWorkBroadcastID
owner_id = vkTestOwnerID if dev else vkStreamOwnerID


def make_vk_post(payload):
    vk_post = requests.get('https://api.vk.com/method/wall.post', params=payload).json()
    post_id = vk_post['response']['post_id']
    data = {'message': {'attachment': f'wall{owner_id}_{post_id}'}}
    headers = {'content-type': 'application/json'}
    broadcast_params = {
        'token': vkBroadcastToken,
        'list_ids': broadcast_id,
        'run_now': 1
    }
    r = requests.post('https://broadcast.vkforms.ru/api/v2/broadcast', params=broadcast_params, data=json.dumps(data), headers=headers)
    if r.status_code == requests.codes.ok:
        print('Broadcast Successful')
    else:
        print('Broadcast Failed')
        print(r.text)


def post_start_time(start_time, user_id, user_num):
    uptimes[user_num] = start_time
    uptime_temp = open(path.join('uptimes', f'{user_id}.txt'), 'w+')
    uptime_temp.write(str(start_time))
    uptime_temp.close()


def send_uptime(user_id, start_time):
    uptime = time.time() - start_time - 300
    formatted = time.strftime("%H:%M:%S", time.gmtime(uptime))
    payload = {'access_token': vkStreamBotKey,
               'v': '5.103',
               'message': f'{get_username(user_id)} стримил {formatted}',
               'chat_id': 1,
               'random_id': getrandbits(64)}
    r = requests.get('https://api.vk.com/method/messages.send', params=payload)
    if r.status_code == requests.codes.ok:
        return 'Successfully send uptime of ' + formatted
    else:
        return 'Uptime sending ERROR'


def get_username(user_id):
    headers = {'Authorization': 'Bearer ' + twitchToken, 'Client-ID': twitchClient}
    params = {'id': user_id}
    response = requests.get('https://api.twitch.tv/helix/users', params=params, headers=headers).json()
    return response['data'][0]['display_name']


def twitch_request():
    for i in range(len(streamerIds)):
        print(streamerIds[i])
        payload = {'user_id': streamerIds[i]}
        headers = {'Authorization': 'Bearer ' + twitchToken, 'Client-ID': twitchClient}
        try:
            r = requests.get('https://api.twitch.tv/helix/streams', params=payload, headers=headers, timeout=5).json()
            info = r['data']
            if info:
                print('User ' + streamerIds[i] + ' is streaming')
                if uptimes[i] == 0:
                    uptime_temp = open(path.join('uptimes', f'{streamerIds[i]}.txt'), 'r')
                    uptimes[i] = float(uptime_temp.read())
                    uptime_temp.close()
                    if uptimes[i] != 0:
                        print('Set ' + streamerIds[i] + ' uptime to ' + time.strftime("%H:%M:%S", time.gmtime(time.time() - uptimes[i])))
                if not flags[i]:
                    if timeout[i] != 0:
                        print(streamerIds[i] + ' resumed streaming')
                        timeout[i] = 0
                        flags[i] = True
                    else:
                        info = info[0]
                        name = get_username(streamerIds[i])
                        print(name + ' started streaming')
                        gameid = info.get('game_id')
                        try:
                            game = requests.get('https://api.twitch.tv/helix/games?id=' + gameid, headers=headers).json()['data'][0]['name']
                        except (IndexError, KeyError):
                            game = ''
                        payload = {'owner_id': owner_id, 'access_token': vkPersKey, 'v': '5.103',
                                   'from_group': '1',
                                   'message': f'{name} сейчас стримит {game} на https://twitch.tv/{name.lower()}',
                                   'attachments': 'https://twitch.tv/' + name.lower()}
                        make_vk_post(payload)
                        flags[i] = True
                        post_start_time(time.time(), streamerIds[i], i)
            elif not info and flags[i]:
                flags[i] = False
                print(f'User {streamerIds[i]} stopped streaming')
                timeout[i] = 1
            else:
                print(f'User {streamerIds[i]} is not streaming')
                if timeout[i] != 0:
                    if timeout[i] > 5:
                        timeout[i] = 0
                        if uptimes[i] != 0:
                            print(send_uptime(streamerIds[i], uptimes[i]))
                    else:
                        timeout[i] += 1
                else:
                    post_start_time(0, streamerIds[i], i)
        except Exception as r:
            print('Error: ' + str(r))


while True:
    twitch_request()
    time.sleep(60)
