#   
#   This program reuploads animations to roblox.
#
#   Copyright (C) 2024 kartFr
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#

from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio
import aiohttp
import subprocess
import threading
import json
import time
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

completedEvent = threading.Event()
completedAnimations = {}
started = False
finished = False
cookie = None
totalIds = 0
idsUploaded = 0

class Config:
    USER_INFO_URL = "https://www.roblox.com/mobileapi/userinfo"
    LATEST_VERSION_URL = "https://api.github.com/repos/kartFr/Auto-Animation-Reuploader/releases/latest"
    ASSET_URL = "https://assetdelivery.roblox.com/v1/asset/?id="
    UPLOAD_URL = "https://www.roblox.com/ide/publish/uploadnewanimation"
    ASSETS_INFO_URL = "https://develop.roblox.com/v1/assets"
    LOGOUT_URL = "https://auth.roblox.com/v2/logout"
    COOKIE_FILE = "cookie.txt"
    VERSION_FILE = "VERSION.txt"
    SERVER_PORT = 6969

async def isValidCookie():
    global cookie
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(Config.USER_INFO_URL, cookies={".ROBLOSECURITY": cookie}) as response:
                await response.json()
        except:
            return False
    return True

def getSavedCookie():
    try:
        with open(Config.COOKIE_FILE) as cookieFile:
            return cookieFile.read()
    except FileNotFoundError:
        return None

def updateSavedCookie():
    global cookie
    try:
        with open(Config.COOKIE_FILE, "w") as cookieFile:
            cookieFile.write(cookie)
    except Exception as e:
        logging.warning(f"Saving cookie failed: {e}")

def getCurrentVersion():
    try:
        with open(Config.VERSION_FILE) as versionFile:
            return versionFile.read().strip()
    except FileNotFoundError:
        return None

async def getLatestVersion():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(Config.LATEST_VERSION_URL) as response:
                latest_version = await response.json()
                return latest_version.get("name")
        except:
            return None

def clearScreen():
    os.system("cls" if os.name == "nt" else "clear")

def updateFile():
    clearScreen()
    logging.info("Updating. Please be patient.")
    dataPath = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    subprocess.Popen(["Python", os.path.join(dataPath, "updater.py")])
    sys.exit()

XSRFTokenEvent = threading.Event()
fetchingXSRFToken = False
XSRFToken = None

async def getXSRFToken():
    global XSRFToken, fetchingXSRFToken
    if fetchingXSRFToken:
        XSRFTokenEvent.wait()
        return
    fetchingXSRFToken = True
    if XSRFToken:
        logging.error("XSRF token expired fetching new one")
    async with aiohttp.ClientSession() as session:
        for _ in range(3):
            try:
                async with session.post(Config.LOGOUT_URL, cookies={".ROBLOSECURITY": cookie}) as response:
                    XSRFToken = response.headers.get("X-CSRF-TOKEN")
                    break
            except:
                logging.error("Failed getting XSRF token, trying in 5 seconds")
                await asyncio.sleep(5)
    fetchingXSRFToken = False
    XSRFTokenEvent.set()
    XSRFTokenEvent.clear()

async def getAssetData(session, assetid):
    try:
        async with session.get(f"{Config.ASSET_URL}{assetid}") as response:
            return await response.content.read()
    except:
        return False

async def publishAsset(session, assetTypeName, name, creatorId, isGroup, assetData):
    try:
        async with session.post(
            f"{Config.UPLOAD_URL}?assetTypeName={assetTypeName}&name={name}&description=kartfr🤑🤑&AllID=1&ispublic=False&allowComments=True&isGamesAsset=False{ '&groupId=' + str(creatorId) if isGroup else '' }",
            data=assetData,
            headers={"X-CSRF-TOKEN": XSRFToken, "User-Agent": "RobloxStudio/WinInet"},
            cookies={".ROBLOSECURITY": cookie}
        ) as response:
            return response
    except Exception as e:
        logging.error(f"Error publishing asset: {e}")
        return None

async def publishAnimation(animationInfo, creatorId, isGroup):
    global completedAnimations, fetchingXSRFToken, idsUploaded, totalIds, XSRFToken, cookie
    animationId = animationInfo["id"]
    name = animationInfo["name"]
    animationCreatorId = animationInfo["creator"]["targetId"]
    assetType = animationInfo["type"]
    newAnimationId = None
    failureReason = None
    animationData = None
    if animationCreatorId == creatorId:
        failureReason = "Owned"
    elif animationCreatorId == 1:
        failureReason = "Roblox"
    elif assetType != "Animation":
        failureReason = "Not Animation"
    for _ in range(5):
        if failureReason:
            break
        if fetchingXSRFToken:
            await getXSRFToken()
        if not animationData:
            async with aiohttp.ClientSession() as session:
                animationData = await getAssetData(session, animationId)
            if not animationData:
                await asyncio.sleep(1)
                continue
        async with aiohttp.ClientSession() as session:
            publishRequest = await publishAsset(session, "Animation", name, creatorId, isGroup, animationData)
        if publishRequest:
            content = await publishRequest.text()
            if content.isnumeric():
                newAnimationId = content
                break
            if publishRequest.status == 422:
                break
            if publishRequest.status == 500:
                name = "[Censored Name]"
                await asyncio.sleep(3)
                continue
            if publishRequest.status == 403 and content == "XSRF Token Validation Failed":
                await getXSRFToken()
                continue
            if content == "Inappropriate name or description.":
                name = "[Censored Name]"
            else:
                logging.error(f"Error found please report:\nCode: {publishRequest.status}\nReason: {publishRequest.reason}\nContent: {content}")
        await asyncio.sleep(1)
    idsUploaded += 1
    if newAnimationId:
        logging.info(f"[{idsUploaded}/{totalIds}] {name}: {animationId} ; {newAnimationId}")
        completedAnimations[animationId] = newAnimationId
    else:
        match failureReason:
            case "Owned":
                logging.warning(f"[{idsUploaded}/{totalIds}] Already own {name}: {animationId}.")
            case "Roblox":
                logging.warning(f"[{idsUploaded}/{totalIds}] {name} is owned by roblox: {animationId}.")
            case "Not Animation":
                logging.warning(f"[{idsUploaded}/{totalIds}] {name} is not an animation: {animationId}.")
            case _:
                logging.error(f"[{idsUploaded}/{totalIds}] Failed to publish {name}: {animationId}.")
    if idsUploaded == totalIds:
        global completedEvent
        completedEvent.set()
        completedEvent.clear()

async def publishAnimationAsync(animationInfo, creatorId, isGroup):
    asyncio.create_task(publishAnimation(animationInfo, creatorId, isGroup))
    animationCreatorId = animationInfo["creator"]["targetId"]
    assetType = animationInfo["type"]
    if animationCreatorId != creatorId and animationCreatorId != 1 and assetType == "Animation":
        await asyncio.sleep(60 / 400)

async def getAssetIdInfo(session, assetIds):
    for _ in range(5):
        try:
            async with session.get(f"{Config.ASSETS_INFO_URL}?assetIds={','.join(str(i) for i in assetIds)}", cookies={".ROBLOSECURITY": cookie}) as response:
                assetInfoList = await response.json()
                return assetInfoList["data"]
        except:
            await asyncio.sleep(1)
            continue

def getMissingIds(ids, assetInfoList):
    global idsUploaded, totalIds
    infoListIds = {animationInfo["id"]: True for animationInfo in assetInfoList}
    for id in ids:
        if int(id) not in infoListIds:
            idsUploaded += 1
            logging.error(f"[{idsUploaded}/{totalIds}] Invalid asset id: {id}.")

def splitArray(array, size):
    return [array[i:i + size] for i in range(0, len(array), size)]

async def bulkPublishAnimations(animations, creatorId, isGroup):
    global totalIds, completedEvent, finished, idsUploaded
    splitAnimations = splitArray(animations, 50)
    totalIds = len(animations)
    startTime = time.time()
    idsUploaded = 0
    await getXSRFToken()
    async with aiohttp.ClientSession() as session:
        for animationList in splitAnimations:
            animationInfoList = await getAssetIdInfo(session, animationList)
            getMissingIds(animationList, animationInfoList)
            for animationInfo in animationInfoList:
                await publishAnimationAsync(animationInfo, creatorId, isGroup)
    if idsUploaded != totalIds:
        completedEvent.wait()
    hours, remainder = divmod(time.time() - startTime, 3600)
    minutes, seconds = divmod(remainder, 60)
    logging.info(f"Publishing took {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds.")
    logging.info("Waiting for client...")
    finished = True

async def bulkPublishAnimationsAsync(animations, creatorId, isGroup):
    asyncio.create_task(bulkPublishAnimations(animations, creatorId, isGroup))

class Requests(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        global finished, completedAnimations
        if finished and len(completedAnimations) == 0:
            global started
            self.wfile.write(bytes(("done").encode("utf-8")))
            logging.info("You may close this terminal. (You can spoof again without restarting if you need to.)")
            finished = False
            started = False
        else:
            currentAnimations = completedAnimations
            completedAnimations = {}
            self.wfile.write(bytes(json.dumps(currentAnimations).encode()))

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        global started
        if started:
            return
        started = True
        contentLength = int(self.headers['Content-Length'])
        recievedData = json.loads(self.rfile.read(contentLength).decode('utf-8'))
        clearScreen()
        logging.info("Uploading animations.")
        asyncio.run(bulkPublishAnimationsAsync(recievedData["animations"], recievedData["creatorId"], recievedData["isGroup"]))

    def log_message(self, *args):
        pass

if __name__ == '__main__':
    cookie = getSavedCookie()
    clearScreen()
    if (latestVersion := asyncio.run(getLatestVersion())) and (getCurrentVersion() != latestVersion):
        logging.warning("Out of date. New update is available on github.")
        update = input("Update?(y/n): ")
        if update.lower() == "y":
            updateFile()
        clearScreen()
    if cookie and not asyncio.run(isValidCookie()):
        logging.error("Cookie expired.")
        cookie = None
    if not cookie:
        while True:
            cookie = input("Cookie: ")
            clearScreen()
            if asyncio.run(isValidCookie()):
                updateSavedCookie()
                break
            elif "WARNING:-DO-NOT-SHARE-THIS." not in cookie:
                logging.error("No Roblox warning in cookie. Include the entire .ROBLOSECURITY warning.")
            else:
                logging.error("Cookie is invalid.")
    logging.info("localhost started, you may start the plugin.")
    server = HTTPServer(("localhost", Config.SERVER_PORT), Requests)
    server.serve_forever()
