import json
import time
from asyncio import sleep
from credentials import vk_personal_token, vk_stream_bot_token, vk_stream_bot_owner_id, vk_broadcast_token, vk_broadcast_id, vk_dev_broadcast_id, twitch_client, \
    streamer_ids, vk_test_bot_owner_id, dev, twitch_token, vk_personal_user_id
from os import path
from vk_botting import Bot, when_mentioned
from traceback import print_exc

uptimes = [0.0] * len(streamer_ids)
flags = [False] * len(streamer_ids) if dev else [True] * len(streamer_ids)
timeout = [0] * len(streamer_ids)
broadcast_id = vk_dev_broadcast_id if dev else vk_broadcast_id
owner_id = vk_test_bot_owner_id if dev else vk_stream_bot_owner_id
tech = vk_personal_user_id if dev else 2000000001

dtguild = Bot(command_prefix=when_mentioned, case_insensitive=True)


@dtguild.listen()
async def on_ready():
    await dtguild.attach_user_token(vk_personal_token)
    await dtguild.loop.create_task(twitch_loop())
    print(f'Logged in as {dtguild.group.name}')


@dtguild.listen()
async def on_wall_reply_new(comment):
    user = await dtguild.get_page(comment.from_id, name_case='gen')
    return await dtguild.send_message(tech, f'Новый комментарий от {user.mention}', attachment=f'wall-{dtguild.group.id}_{comment.id}')


@dtguild.listen()
async def on_wall_post_new(post):
    user = await dtguild.get_user(post.created_by, name_case='gen')
    await dtguild.send_message(tech, f'Новый пост от {user.mention}', attachment=f'wall-{dtguild.group.id}_{post.id}')
    params = {
        'token': vk_broadcast_token,
        'run_now': 1
    }
    data = json.dumps({'message': {'attachment': f'wall-{dtguild.group.id}_{post.id}'}})
    if '#dtguild_новости' in post.text.lower():
        params['list_ids'] = 437143
    elif '#dtguild_анонс' in post.text.lower():
        params['list_ids'] = 437141
    elif '#dtguild_оффтоп' in post.text.lower():
        params['list_ids'] = 489597
    else:
        return
    await dtguild.session.post('https://broadcast.vkforms.ru/api/v2/broadcast', params=params, data=data)


@dtguild.listen()
async def on_message_new(msg):
    if msg.from_id == msg.peer_id:
        user = await dtguild.get_user(msg.from_id, name_case='gen')
        return await dtguild.send_message(tech, f'Новое сообщение от {user.mention}', forward_messages=msg.id)


@dtguild.listen()
async def on_group_join(user, _):
    return await dtguild.send_message(tech, f'Новый подписчик в группе: {user.mention}')


async def make_vk_post(name, game):
    vk_post = await dtguild.user_vk_request('wall.post', message=f'{name} сейчас стримит {game} на https://twitch.tv/{name.lower()}',
                                            attachments='https://twitch.tv/' + name.lower(), from_group=1, owner_id=owner_id)
    post_id = vk_post['response']['post_id']
    data = {'message': {'attachment': f'wall{owner_id}_{post_id}'}}
    headers = {'content-type': 'application/json'}
    broadcast_params = {
        'token': vk_broadcast_token,
        'list_ids': broadcast_id,
        'run_now': 1
    }
    await dtguild.session.post('https://broadcast.vkforms.ru/api/v2/broadcast', params=broadcast_params, data=json.dumps(data), headers=headers)


def post_start_time(start_time, user_id, user_num):
    uptimes[user_num] = start_time
    with open(path.join('uptimes', f'{user_id}.txt'), 'w+') as uptime:
        uptime.write(str(start_time))


async def send_uptime(user_id, start_time):
    uptime = time.time() - start_time - 300
    formatted = time.strftime("%H:%M:%S", time.gmtime(uptime))
    name = await get_username(user_id)
    await dtguild.send_message(tech, f'{name} стримил {formatted}')


async def get_username(user_id):
    headers = {'Authorization': 'Bearer ' + twitch_token, 'Client-ID': twitch_client}
    params = {'id': user_id}
    response = await dtguild.session.get('https://api.twitch.tv/helix/users', params=params, headers=headers)
    response = await response.json()
    return response['data'][0]['display_name']


async def twitch_request():
    url = 'https://api.twitch.tv/helix/streams?user_id' + '&user_id='.join(streamer_ids)
    headers = {'Authorization': 'Bearer ' + twitch_token, 'Client-ID': twitch_client}
    res = await dtguild.session.get(url, headers=headers)
    res = await res.json()
    info = {}
    for stream in res['data']:
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
                        name = await get_username(streamer)
                        print(name + ' started streaming')
                        gameid = streamer_info.get('game_id')
                        try:
                            game = await dtguild.session.get('https://api.twitch.tv/helix/games?id=' + gameid, headers=headers)
                            game = (await game.json())['data'][0]['name']
                        except (IndexError, KeyError):
                            game = ''
                        await make_vk_post(name, game)
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
                            await send_uptime(streamer, uptimes[i])
                    else:
                        timeout[i] += 1
                else:
                    post_start_time(0, streamer, i)
        except Exception as r:
            print(f'Error: {r}')
            print_exc()


async def twitch_loop():
    while True:
        await twitch_request()
        await sleep(60)


dtguild.run(vk_stream_bot_token)
