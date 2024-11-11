from urllib.parse import unquote
from pyrogram import Client
from data import config
from utils.core import logger

from aiohttp_socks import ProxyConnector
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName
from fake_useragent import UserAgent
from pathlib import Path

import os
import json
import aiofiles
import aiohttp
import asyncio
import random


class Paws:

    def __init__(self, thread: int, account: str, proxy=None):
        self.session = None
        self.UserAgent = None
        self.device = 'android'
        self.user_info = None
        self.token = None
        self.auth_url = None
        self.thread = thread
        self.name = account
        self.ref = config.REF_CODE
        if proxy:
            proxy_client = {
                "scheme": config.PROXY_TYPE,
                "hostname": proxy.split(':')[0],
                "port": int(proxy.split(':')[1]),
                "username": proxy.split(':')[2],
                "password": proxy.split(':')[3],
            }
            self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR,
                                 proxy=proxy_client)
        else:
            self.client = Client(name=account, api_id=config.API_ID, api_hash=config.API_HASH, workdir=config.WORKDIR)

        if proxy:
            self.proxy = f"{config.PROXY_TYPE}://{proxy.split(':')[2]}:{proxy.split(':')[3]}@{proxy.split(':')[0]}:{proxy.split(':')[1]}"
        else:
            self.proxy = None

        self.auth_token = ""

    async def create_session(self):
        connector = ProxyConnector.from_url(self.proxy) if self.proxy else aiohttp.TCPConnector(verify_ssl=False)
        browser_version = self.UserAgent.split("Chrome/")[1].split(".")[0]
        headers = {
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://app.paws.community',
            'priority': 'u=1, i',
            'referer': 'https://app.paws.community/',
            'pragma':'no-cache',
            'sec-ch-ua': f'"Chromium";v="{browser_version}", "Google Chrome";v="{browser_version}", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': f'"{self.device}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.UserAgent
        }

        return aiohttp.ClientSession(headers=headers, trust_env=True, connector=connector)

    async def set_useragent(self):
        try:
            file_path = os.path.join(os.path.join(Path(__file__).parent.parent, "data"), "UserAgent.json")

            if not os.path.exists(file_path):
                data = {self.name: UserAgent(os=self.device).random}
                async with aiofiles.open(file_path, 'w', encoding="utf-8") as file:
                    await file.write(json.dumps(data, ensure_ascii=False, indent=4))

                self.UserAgent = data[self.name]
                return True

            else:
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                        content = await file.read()
                        data = json.loads(content)

                    if self.name in data:
                        self.UserAgent = data[self.name]
                        return True

                    else:
                        self.UserAgent = UserAgent(os=self.device).random
                        data[self.name] = self.UserAgent

                        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
                            await file.write(json.dumps(data, ensure_ascii=False, indent=4))

                        return True
                except json.decoder.JSONDecodeError:
                    logger.error(f"useragent | Thread {self.thread} | {self.name} | syntax error in UserAgents json file!")
                    return False

        except Exception as err:
            logger.error(f"useragent | Thread {self.thread} | {self.name} | {err}")
            return False

    async def main(self):
        await asyncio.sleep(random.randint(*config.ACC_DELAY))
        try:
            useragent = await self.set_useragent()
            if not useragent:
                logger.error(f"UserAgent | Thread {self.thread} | {self.name} | Invalid User Agent!")
                return 0
            self.session = await self.create_session()
            try:
                login = await self.login()
                if login is False:
                    raise Exception("Failed to log in!")
                logger.info(f"main | Thread {self.thread} | {self.name} | Start! | PROXY : {self.proxy}")
            except Exception as err:
                logger.error(f"main | Thread {self.thread} | {self.name} | {err}")
                await asyncio.sleep(random.uniform(300, 450))
                await self.session.close()

            await asyncio.sleep(random.randint(*config.MINI_SLEEP))
            tasks = await self.list()
            if tasks:
                random.shuffle(tasks)
                for task in tasks:
                    if task["type"] == "social" and not task['progress']['claimed']:
                        if "t.me" in task["data"] and ("Follow" in task["title"] or "Channel" in task["title"]):
                            if task['progress']['total'] > task['progress']['current']:
                                async with self.client:
                                    if task["data"].startswith("https://t.me/+"):
                                        await self.client.join_chat(task["data"])
                                    else:
                                        await self.client.join_chat(task['data'].split('/')[-1])

                                    await asyncio.sleep(random.randint(*config.TASK_SLEEP))
                                    await self.completed(task)

                            elif task['progress']['total'] == task['progress']['current']:
                                await asyncio.sleep(random.randint(*config.MINI_SLEEP))
                                await self.claim(task)

                        if task["action"] == "link":
                            if task['progress']['total'] > task['progress']['current']:
                                await asyncio.sleep(random.randint(*config.TASK_SLEEP))
                                await self.completed(task)
                            elif task['progress']['total'] == task['progress']['current']:
                                await asyncio.sleep(random.randint(*config.MINI_SLEEP))
                                await self.claim(task)

                    elif task["type"] == "referral" and not task['progress']['claimed']:
                        if task['progress']['total'] == task['progress']['current']:
                            await asyncio.sleep(random.randint(*config.MINI_SLEEP))
                            await self.claim(task)

                    elif task["type"] == "emojiName":
                        if task['progress']['total'] > task['progress']['current']:
                            await self.client.connect()
                            user = await self.client.get_me()
                            user_name = user.first_name
                            new_user_name = user_name + " 🐾"
                            await self.client.update_profile(first_name=new_user_name)
                            await self.client.disconnect()
                            await asyncio.sleep(random.randint(*config.TASK_SLEEP))
                            await self.completed(task)
                        elif task['progress']['total'] == task['progress']['current']:
                            await asyncio.sleep(random.randint(*config.MINI_SLEEP))
                            await self.claim(task)

            logger.info(f"main | Thread {self.thread} | {self.name} | Account terminated!")
            await self.session.close()
            return 0

        except Exception as err:
            logger.error(f"main | Thread {self.thread} | {self.name} | {err}")
            await self.session.close()
            return 0

        return False

    async def list(self):
        del self.session.headers['content-length']
        response = await self.session.get("https://api.paws.community/v1/quests/list")
        if response.status == 200:
            response = await response.json()
            if response['success']:
                return response['data']
            else:
                return False
        return False

    async def completed(self, task):
        body = {'questId': task['_id']}
        body_json = json.dumps(body)
        content_length = str(len(body_json.encode('utf-8')))
        self.session.headers['content-length'] = content_length
        response = await self.session.post("https://api.paws.community/v1/quests/completed", json=body)
        if response.status == 201:
            response = await response.json()
            if response['success']:
                logger.info(
                    f"task | Thread {self.thread} | {self.name} | Task completed: {task['title']}")
                return True
            else:
                logger.warning(
                    f"task | Thread {self.thread} | {self.name} | Failed to complete task: {task['title']}")
                return False
        logger.warning(
            f"task | Thread {self.thread} | {self.name} | Failed to complete task: {task['title']}")
        return False

    async def claim(self, task):
        body = {'questId': task['_id']}
        body_json = json.dumps(body)
        content_length = str(len(body_json.encode('utf-8')))
        self.session.headers['content-length'] = content_length
        response = await self.session.post("https://api.paws.community/v1/quests/claim", json=body)
        if response.status == 201:
            response = await response.json()
            if response['success']:
                logger.success(
                    f"task | Thread {self.thread} | {self.name} | Task claimed: {task['title']}")
                return True
            else:
                logger.success(
                    f"task | Thread {self.thread} | {self.name} | Failed to claim task: {task['title']}")
                return False
        logger.warning(
            f"task | Thread {self.thread} | {self.name} | Failed to complete task: {task['title']}")
        return False

    async def get_tg_web_data(self):
        async with self.client:
            try:
                web_view = await self.client.invoke(RequestAppWebView(
                    peer=await self.client.resolve_peer('PAWSOG_bot'),
                    app=InputBotAppShortName(bot_id=await self.client.resolve_peer('PAWSOG_bot'), short_name="PAWS"),
                    platform=self.device,
                    write_allowed=True,
                    start_param=self.ref
                ))

                self.auth_url = web_view.url
                self.user_info = await self.client.get_me()
            except Exception as err:
                logger.error(f"main | Thread {self.thread} | {self.name} | {err}")
                if 'USER_DEACTIVATED_BAN' in str(err):
                    logger.error(f"login | Thread {self.thread} | {self.name} | USER BANNED")
                    await self.client.disconnect()
                    return False
            return unquote(string=self.auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

    async def login(self):
        try:
            tg_web_data = await self.get_tg_web_data()
            if tg_web_data is False:
                return False

            body = {'data': tg_web_data, 'referralCode': self.ref}
            body_json = json.dumps(body)
            content_length = str(len(body_json.encode('utf-8')))
            self.session.headers['content-length'] = content_length
            response = await self.session.post('https://api.paws.community/v1/user/auth', json=body)
            response = await response.json()
            if response["success"]:
                self.token = response['data'][0]
                self.session.headers['Authorization'] = "Bearer " + self.token
                return True
            else:
                return False
        except Exception as err:
            logger.error(f"login | Thread {self.thread} | {self.name} | {err}")
            return False
