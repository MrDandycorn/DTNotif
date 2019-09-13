import requests
import json
import time
from credentials import vkPersUserID, vkPersKey, vkStreamOwnerID, twitchKeyToken, vkBroadcastToken, vkWorkBroadcastID, twitchClient, streamerIds

uptimes = [0.0] * len(streamerIds)
flags = [True] * len(streamerIds)
timeout = [0] * len(streamerIds)
i = 1
twitchKey = requests.get('http://twitch.center/customapi/quote?token=' + twitchKeyToken + '&data=1&no_id=1')
twitchKey = twitchKey.text


def vkPost(payload):
    vkReq = requests.get(requests.Request('GET', 'https://api.vk.com/method/wall.post', params=payload).prepare().url)
    print(vkReq.text)
    tempdict = vkReq.json()
    postID = tempdict.get('response').get('post_id')
    data = {'message': {'attachment': 'wall' + vkPersUserID + '_' + str(postID)}}
    headers = {'content-type': 'application/json'}
    r = requests.post(
        'https://broadcast.vkforms.ru/api/v2/broadcast?token=' + vkBroadcastToken + '&list_ids=' + vkWorkBroadcastID + '&run_now=1',
        data=json.dumps(data), headers=headers)
    if r.status_code == requests.codes.ok:
        print('Broadcast Successful')
    else:
        print('Broadcast Failed')
        print(r.text)


def postStartTime(startTime, userID, userNum):
    uptimes[userNum] = startTime
    uptimeTemp = open(r'uptimes/' + userID + '.txt', 'w+')
    uptimeTemp.write(str(startTime))
    uptimeTemp.close()


def sendUptime(userID, startTime):
    uptime = time.time() - startTime - 300
    formatted = time.strftime("%H:%M:%S", time.gmtime(uptime))
    payload = {'access_token': vkBroadcastToken, 'v': '5.80',
               'message': getUserName(userID) + ' стримил ' + formatted,
               'chat_id': '1'}
    r = requests.get('https://api.vk.com/method/messages.send', params=payload)
    if r.status_code == requests.codes.ok:
        return 'Successfully send uptime of ' + formatted
    else:
        return 'Uptime sending ERROR'


def getUserName(user_id):
    headers = {'authorization': 'Bearer ' + twitchKey}
    userName = requests.get('https://api.twitch.tv/helix/users?client_id=' + twitchClient + '&id=' + user_id,
                            headers=headers)
    tempdict = json.loads(userName.text)
    userName = tempdict.get('data')[0]
    userName = userName.get('display_name')
    return userName


def twitchRequest():
    for i in range(len(streamerIds)):
        print(streamerIds[i])
        payload = {'user_id': streamerIds[i], 'client_id': twitchClient}
        headers = {'authorization': 'Bearer ' + twitchKey}
        try:
            r = requests.get('https://api.twitch.tv/helix/streams', params=payload, headers=headers, timeout=5)
            # r = requests.get('https://google.com:81',timeout=1)        #timeout bugs testing
            tempdict = json.loads(r.text)
            info = tempdict.get('data')
            if info:
                print('User ' + streamerIds[i] + ' is streaming')
                if uptimes[i] == 0:
                    uptimeTemp = open(
                        r'uptimes/' + streamerIds[i] + '.txt', 'r')
                    uptimes[i] = float(uptimeTemp.read())
                    uptimeTemp.close()
                    if uptimes[i] != 0:
                        print('Set ' + streamerIds[i] + ' uptime to ' + time.strftime("%H:%M:%S",
                                                                                      time.gmtime(
                                                                                          time.time() - uptimes[i])))
                if not flags[i]:
                    if timeout[i] != 0:
                        print(streamerIds[i] + ' resumed streaming')
                        timeout[i] = 0
                        flags[i] = True
                    else:
                        info = info[0]
                        name = getUserName(streamerIds[i])
                        print(name + ' started streaming')
                        gameid = info.get('game_id')
                        game = requests.get('https://api.twitch.tv/helix/games?id=' + gameid, headers=headers)
                        tempdict = json.loads(game.text)
                        try:
                            game = tempdict.get('data')[0]
                            game = game.get('name')
                        except IndexError:
                            game = ''
                        payload = {'owner_id': vkStreamOwnerID, 'access_token': vkPersKey, 'v': '5.95',
                                   'from_group': '1',
                                   'message': name + ' сейчас стримит ' + game + ' на https://twitch.tv/' + name.lower(),
                                   'attachments': 'https://twitch.tv/' + name.lower()}
                        vkPost(payload)
                        flags[i] = True
                        postStartTime(time.time(), streamerIds[i], i)
            elif not info and flags[i]:
                flags[i] = False
                print('User ' + streamerIds[i] + ' stopped streaming')
                timeout[i] = 1
            else:
                print('User ' + streamerIds[i] + ' is not streaming')
                if timeout[i] != 0:
                    if timeout[i] > 5:
                        timeout[i] = 0
                        if uptimes[i] != 0:
                            print(sendUptime(streamerIds[i], uptimes[i]))
                    else:
                        timeout[i] += 1
                else:
                    postStartTime(0, streamerIds[i], i)
        except Exception as r:
            print('Error: ' + str(r))


while True:
    twitchRequest()
    time.sleep(60)
    i += 1
    if i == 30000:
        i = 0
        twitchKey = requests.get('http://twitch.center/customapi/quote?token=' + twitchKeyToken + '&data=1&no_id=1')
        twitchKey = twitchKey.text
        print('Token Updated')
