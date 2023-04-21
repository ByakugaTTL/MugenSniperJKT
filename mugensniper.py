from aiohttp import TCPConnector
from concurrent.futures import ThreadPoolExecutor
from asyncio import Semaphore
import colorsys
from tqdm import tqdm
import json
import ujson
import time
import os
from datetime import datetime, timedelta
import uuid
import asyncio
import random
import requests
import configparser
from colorama import Fore, Back, Style
import aiohttp
from termcolor import colored
import ctypes
import sys
import tkinter as tk
from PIL import ImageTk, Image
import urllib.request


# Add your widgets and functions here

ctypes.windll.kernel32.SetConsoleTitleW("Mugen Sniper [<>]")
# Get a handle to the console buffer
handle = ctypes.windll.kernel32.GetStdHandle(-11)
# Set the console screen buffer size
ctypes.windll.kernel32.SetConsoleScreenBufferSize(handle, ctypes.wintypes._COORD(150, 150))
# Set the console window size
rect = ctypes.wintypes.SMALL_RECT(0, 0, 149, 149)
ctypes.windll.kernel32.SetConsoleWindowInfo(handle, True, ctypes.byref(rect))
config = configparser.ConfigParser()
config.read('config.ini')


class Sniper:
    def __init__(self) -> None:
        self.start_time = datetime.now()
        self.webhookEnabled = "configWebhook" in config and config["configWebhook"]["enabled"] == "on"
        self.webhookUrl = config["configWebhook"]["webhook"] if self.webhookEnabled else None
        self.accounts = None
        self.items = self._load_items()
        self.title = """
$$\      $$\                                     
$$$\    $$$ |                                    
$$$$\  $$$$ $$\   $$\ $$$$$$\  $$$$$$\ $$$$$$$\  
$$\$$\$$ $$ $$ |  $$ $$  __$$\$$  __$$\$$  __$$\ 
$$ \$$$  $$ $$ |  $$ $$ /  $$ $$$$$$$$ $$ |  $$ |
$$ |\$  /$$ $$ |  $$ $$ |  $$ $$   ____$$ |  $$ |
$$ | \_/ $$ \$$$$$$  \$$$$$$$ \$$$$$$$\$$ |  $$ |
\__|     \__|\______/ \____$$ |\_______\__|  \__|
                     $$\   $$ |                  
                     \$$$$$$  |                  
                      \______/                   """
        
        self.checks = 0
        self.buys = 0
        self.request_method = 2
        self.total_ratelimits = 0
        self.last_time = 0
        self.errors = 0
        self.clear = "cls" if os.name == 'nt' else "clear"
        self.version = "0.2"
        self.task = None
        self.scraped_ids = []
        self.latest_free_item = {}
        self._setup_accounts()
        self.semaphore = asyncio.Semaphore(1)
        
    # self.check_version()
        
        magenta = "\033[35m"
        yellow = "\033[33m"
        end = "\033[0m"
        green = "\033[32m"

        # Loading bar code starts here
        toolbar_width = 40

        # setup toolbar
        sys.stdout.write(f"{magenta}Loading...{end} [%s]" % (" " * toolbar_width))
        sys.stdout.flush()
        sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

        for i in range(toolbar_width):
            time.sleep(0.01) # do real work here
            # update the bar
            sys.stdout.write(f"{green}■{end}")
            sys.stdout.flush()

        sys.stdout.write("]\n") # this ends the progress bar

        prompt = f"{magenta}Please specify the time you would like the sniping process to begin (e.g. 3:30am) or enter 'skip' to start immediately: {end}"
        for char in prompt:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.01)

        timestamp_input = input()

        if timestamp_input.lower() == 'skip':
            for char in f"V: {yellow}{self.version}{end} - {yellow}{self.title}{end} - {magenta}Skipping wait and starting snipe process immediately\n":
                sys.stdout.write(char)
                sys.stdout.flush()
                time.sleep(0.01)
        else:
            target_time = datetime.strptime(timestamp_input, '%I:%M%p').time()
            current_time = datetime.now().time()
            while current_time < target_time:
                current_time = datetime.now().time()
                for char in f"V: {yellow}{self.version}{end} - {yellow}Mugen{end} - {magenta}Waiting for snipe process to begin at {yellow}{target_time.strftime('%I:%M %p')}\n":
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    time.sleep(0.0000001)

        asyncio.run(self.start())

    class DotDict(dict):
        def __getattr__(self, attr):
            return self[attr]
    
    def _setup_accounts(self) -> None:
        self.task = "Account Loader"
        self._print_stats
        cookies = self._load_cookies()
        for i in cookies:
              response = asyncio.run(self._get_user_id(cookies[i]["cookie"]))
              response2 = asyncio.run(self._get_xcsrf_token(cookies[i]["cookie"]))
              cookies[i]["id"] = response
              cookies[i]["xcsrf_token"] = response2["xcsrf_token"]
              cookies[i]["created"] = response2["created"]
        self.accounts = cookies
        #1
    def _load_cookies(self) -> dict:
        magenta = '\033[95m'
        end = '\033[0m'
        try:
            with open("cookie.txt", "r") as file:
                lines = file.read().split('\n')
                if not lines:
                    print(f"{magenta}The cookie.txt file is empty.{end}")
                    raise Exception("The cookie.txt file is empty.")
                my_dict = {}
                for i, line in enumerate(lines):
                    my_dict[str(i+1)] = {}
                    my_dict[str(i+1)] = {"cookie": line}
                return my_dict
        except FileNotFoundError:
            print(f"{magenta}The cookie.txt file was not found.{end}")
            raise Exception(f"{magenta}The cookie.txt file was not found.{end}")

    def _load_items(self) -> list:
        magenta = '\033[95m'
        end = '\033[0m'
        try:
            with open('limiteds.txt', 'r') as f:
                content = f.read()
                lines = content.split(',')
            if not lines:
                print(f"{magenta}The limiteds.txt file is empty.{end}")
                raise Exception(f"The limiteds.txt file is empty.{end}")
            return lines
        except FileNotFoundError:
            print(f"{magenta}The limiteds.txt file was not found.{end}")
            raise Exception(f"{magenta}The limiteds.txt file was not found.{end}")
            
            
    async def _get_user_id(self, cookie) -> str:
       async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": cookie}) as client:
           response = await client.get("https://users.roblox.com/v1/users/authenticated", ssl = False)
           data = await response.json()
           if data.get('id') == None:
              raise Exception("Couldn't scrape user id. Error:", data)
           return data.get('id')
    
    def _print_stats(self) -> None:
        yellow = '\033[93m'
        magenta = '\033[95m'
        end = '\033[0m'
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elapsed_time = datetime.now() - self.start_time

        print(f"V: {yellow}{self.version}{end}{magenta} Timestamp: {yellow}{current_time}{end}")
        print(f"T:{magenta}⤍ Time Elapsed: {yellow}{elapsed_time}{magenta} {end}")
        print(f"{yellow}{self.title}{end}")
        print(f"{magenta}⤍ Sniped Items: {yellow}{self.buys}{magenta} {end}")
        print(f"{magenta}⤍ Errors: {yellow}{self.errors}{magenta} {end}")
        print(f"{magenta}⤍ Speed Taken: {yellow}{self.last_time}{magenta} {end}")
        print(f"{magenta}⤍ Roblox ratelimits: {yellow}{self.total_ratelimits}{magenta} {end}")
        print(f"{magenta}⤍ Total iterations: {yellow}{self.checks}{magenta} {end}")

        rainbow_task = ""
        for i, char in enumerate(self.task):
            hue = (i / len(self.task)) * 360
            r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(hue / 360, 1.0, 1.0)]
            rainbow_task += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
        print(f"{magenta}⤍ NT: {rainbow_task}{magenta} {end}")

    async def _get_xcsrf_token(self, cookie) -> dict:
        async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": cookie}) as client:
              response = await client.post("https://accountsettings.roblox.com/v1/email", ssl = False)
              xcsrf_token = response.headers.get("x-csrf-token")
              if xcsrf_token is None:
                 raise Exception("An error occurred while getting the X-CSRF-TOKEN. "
                            "Probably an invalid roblox cookie")
              return {"xcsrf_token": xcsrf_token, "created": datetime.now()}
    
    async def _check_xcsrf_token(self) -> bool:
      for i in self.accounts:
        if self.accounts[i]["xcsrf_token"] is None or \
                datetime.now() > (self.accounts[i]["created"] + timedelta(minutes=10)):
            try:
                response = await self._get_xcsrf_token(self.accounts[i]["cookie"])
                self.accounts[i]["xcsrf_token"] = response["xcsrf_token"]
                self.accounts[i]["created"] = response["created"]
                return True
            except Exception as e:
                print(f"{e.__class__.__name__}: {e}")
                return False
        return True
      return False
    
    async def _check_limiteds(self) -> None:
        async with aiohttp.ClientSession() as session:
            url = "https://catalog.roblox.com/v1/search/items/details?category=All&limit=30&sortType=RecentlyUpdated&subcategory=Collectibles&cursor="
            cursor = ""
            while True:
                try:
                    async with session.get(url + cursor, ssl=False) as response:
                        data = await response.json()
                        if not data.get("data"):
                            break
                        for item in data["data"]:
                            if item["id"] in self.items and item["id"] not in self.scraped_ids:
                                self.scraped_ids.append(item["id"])
                                message = f"New limited dropped: {item['name']} (https://www.roblox.com/catalog/{item['id']})"
                                await self._send_discord_webhook(message)
                except Exception as e:
                    print(f"Error checking limiteds: {e}")
                cursor = data["nextPageCursor"]
                await asyncio.sleep(5)
     
    async def buy_item(self, item_id: int, price: int, user_id: int, creator_id: int, product_id: int, cookie: str, x_token: str) -> None:
        """ Purchase a limited item on Roblox.
        """
        data = {
            "collectibleItemId": item_id,
            "expectedCurrency": 1,
            "expectedPrice": price,
            "expectedPurchaserId": user_id,
            "expectedPurchaserType": "User",
            "expectedSellerId": creator_id,
            "expectedSellerType": "User",
            "idempotencyKey": "random uuid4 string that will be your key or smthn",
            "collectibleProductId": product_id
        }
        total_errors = 0
        async with aiohttp.ClientSession(connector=TCPConnector) as client:
            while True:
                if total_errors >= 10:
                    print("Too many errors encountered. Aborting purchase.")
                    return
                data["idempotencyKey"] = str(uuid.uuid4())
                try:
                    response = await client.post(f"https://apis.roblox.com/marketplace-sales/v1/item/{item_id}/purchase-item", json=data, headers={"x-csrf-token": x_token}, cookies={".ROBLOSECURITY": cookie}, ssl = False)
                except aiohttp.ClientConnectorError as e:
                    self.errors += 1
                    print(f"Connection error encountered: {e}. Retrying purchase...")
                    total_errors += 1
                    continue
                if response.status == 429:
                    print("Ratelimit encountered. Retrying purchase in 1 second...")
                    await asyncio.sleep(1)
                    continue
                try:
                    json_response = await response.json()
                except aiohttp.ContentTypeError as e:
                    self.errors += 1
                    print(f"JSON decode error encountered: {e}. Retrying purchase...")
                    total_errors += 1
                    continue
                if not json_response["purchased"]:
                    self.errors += 1
                    print(f"Purchase failed. Response: {json_response}. Retrying purchase...")
                    total_errors += 1
                else:
                    print(f"Purchase successful. Response: {json_response}.")
                    self.buys += 1
                    if self.webhookEnabled:
                        embed_data = {
                            "title": "New item sniped [MUGEN]",
                            "url": f"https://www.roblox.com/catalog/{item_id}/Mugen",
                            "color": 27839,
                            "author": {
                                "name": "Purchased limited successfully!"
                            },
                            "footer": {
                                "text": "MugenJKT"
                            }
                        }
                        requests.post(self.webhookUrl, json={"content": None, "embeds": [embed_data]})
                    


    async def auto_search(self) -> None:
        self.scraped_ids = set()
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=None)) as session:
            pbar = tqdm(total=100, bar_format=Fore.YELLOW + "{l_bar}{bar}" + Style.RESET_ALL + "|{n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
            while True:
                try:
                    async with session.get("https://catalog.roblox.com/v1/search/items/details?Keyword=orange%20teal%20cyan%20red%20green%20topaz%20yellow%20wings%20maroon%20space%20dominus%20lime%20mask%20mossy%20wooden%20crimson%20salmon%20brown%20pastel%20%20ruby%20diamond%20creatorname%20follow%20catalog%20link%20rare%20emerald%20chain%20blue%20deep%20expensive%20furry%20hood%20currency%20coin%20royal%20navy%20ocean%20air%20white%20cyber%20ugc%20verified%20black%20purple%20yellow%20violet%20description%20dark%20bright%20rainbow%20pink%20cyber%20roblox%20multicolor%20light%20gradient%20grey%20gold%20cool%20indigo%20test%20hat%20limited2%20headphones%20emo%20edgy%20back%20front%20lava%20horns%20water%20waist%20face%20neck%20shoulders%20collectable&Category=11&Subcategory=19&CurrencyType=3&MaxPrice=0&salesTypeFilter=2&SortType=3&limit=30") as response:
                        response.raise_for_status()
                        items = (await response.json())['data']
                        for item in items:
                            if item["id"] not in self.scraped_ids:
                                print(f"Found new item: {item['name']} (ID: {item['id']})")
                                self.latest_free_item = item
                                self.scraped_ids.add(item["id"])
                            if self.latest_free_item.get("priceStatus", "Off Sale") == "Off Sale":
                                continue
                            if self.latest_free_item.get("collectibleItemId") is None:
                                continue
                            productid_response = await session.post("https://apis.roblox.com/marketplace-items/v1/items/details", json={"itemIds": [self.latest_free_item["collectibleItemId"]]}, headers={"x-csrf-token": self.accounts[str(random.randint(1, len(self.accounts)))]["xcsrf_token"], 'Accept': "application/json"}, cookies={".ROBLOSECURITY": self.accounts[str(random.randint(1, len(self.accounts)))]["cookie"]}, ssl = False)
                            response.raise_for_status()
                            productid_data = (await productid_response.json())[0]
                            coroutines = [self.buy_item(item_id = self.latest_free_item["collectibleItemId"], price = 0, user_id = self.accounts[i]["id"], creator_id = self.latest_free_item['creatorTargetId'], product_id = productid_data['collectibleProductId'], cookie = self.accounts[i]["cookie"], x_token = self.accounts[i]["xcsrf_token"]) for i in self.accounts]
                            self.task = "Item Sniper"
                            await asyncio.gather(*coroutines)
                except (aiohttp.client_exceptions.ClientConnectorError, aiohttp.client_exceptions.ServerDisconnectedError, aiohttp.client_exceptions.ClientOSError, aiohttp.client_exceptions.ClientResponseError) as e:
                    print(f"Error: {e}")
                    self.errors += 1
                finally:
                    pbar.update(1)
                    if pbar.n >= 100:
                        pbar.close()
                        pbar = tqdm(total=100, bar_format=Fore.GREEN + "{l_bar}{bar}" + Style.RESET_ALL + "|{n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
                    self.checks += 1
                    await asyncio.sleep(5)

    async def given_id_sniper(self) -> None:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=None)) as session:
            while True:
                try:
                    self.task = "Item Sniper"
                    t0 = asyncio.get_event_loop().time()
                    with ThreadPoolExecutor() as executor:
                        loop = asyncio.get_event_loop()
                        tasks = [asyncio.wrap_future(asyncio.run_coroutine_threadsafe(self.process_item(session, currentItem), loop)) for currentItem in self.items]
                        await asyncio.gather(*tasks)
                    t1 = asyncio.get_event_loop().time()
                    self.last_time = round(t1 - t0, 3)
                except aiohttp.ClientConnectorError as e:
                    print(f'Connection error: {e}')
                    self.errors += 1
                except aiohttp.ContentTypeError as e:
                    print(f'Content type error: {e}')
                    self.errors += 1
                except aiohttp.ClientResponseError as e:
                    print(f'Response error: {e}')
                    self.errors += 1
                except aiohttp.client_exceptions.ClientResponseError as e:
                    print(f"Response Error: {e}")
                finally:
                    self.checks += 1
                await asyncio.sleep(1)

    
    async def process_item(self, session, currentItem):
        async with self.semaphore:
            if not currentItem.isdigit():
                raise Exception(f"Invalid item id given ID: {currentItem}")
            currentAccount = self.accounts[str(random.randint(1, len(self.accounts)))]
            async with session.post("https://catalog.roblox.com/v1/catalog/items/details", json={"items": [{"itemType": "Asset", "id": int(currentItem)}]}, headers={"x-csrf-token": currentAccount['xcsrf_token'], 'Accept': "application/json"}, cookies={".ROBLOSECURITY": currentAccount["cookie"]}, ssl=False) as response:
                response.raise_for_status()
                json_response = await response.json()
                json_response = json_response['data'][0]
                if json_response.get("priceStatus") != "Off Sale" and 0 if json_response.get('unitsAvailableForConsumption') is None else json_response.get('unitsAvailableForConsumption') > 0:
                    productid_response = await session.post("https://apis.roblox.com/marketplace-items/v1/items/details", json={"itemIds": [json_response["collectibleItemId"]]}, headers={"x-csrf-token": currentAccount["xcsrf_token"], 'Accept': "application/json"}, cookies={".ROBLOSECURITY": currentAccount["cookie"]}, ssl=False)
                    response.raise_for_status()
                    productid_data = await productid_response.json()
                    productid_data = productid_data[0]
                    coroutines = [self.buy_item(item_id=json_response["collectibleItemId"], price=json_response['price'], user_id=self.accounts[i]["id"], creator_id=json_response['creatorTargetId'], product_id=productid_data['collectibleProductId'], cookie=self.accounts[i]["cookie"], x_token=self.accounts[i]["xcsrf_token"]) for i in self.accounts]
                    self.task = "ITEM SNIPER"
                    await asyncio.gather(*coroutines)
    
    async def start(self):
            coroutines = []
            coroutines.append(self.given_id_sniper())
            coroutines.append(self.auto_search())
            coroutines.append(self.auto_update())
            await asyncio.gather(*coroutines)
    
    async def auto_update(self):
        while True:
            if not await self._check_xcsrf_token():
                raise Exception("x_csrf_token couldn't be generated")
            os.system(self.clear)
            self._print_stats()
            await asyncio.sleep(1)
        
sniper = Sniper()
sniper


