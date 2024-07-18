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
import subprocess
import threading
import requests
import json
import time
import sys
import os

completedEvent = threading.Event()
completedAnimations = {}
started = False
finished = False
cookie = None
totalIds = 0
idsUploaded = 0

def isValidCookie():
    global cookie
    
    try:
       json.loads(requests.get(
            "https://www.roblox.com/mobileapi/userinfo",
            cookies={".ROBLOSECURITY": cookie}
    ).content)
    except:
        return False
    return True


def getSavedCookie():
    try:
        cookieFile = open("cookie.txt")
    except:
        return None
    return cookieFile.read()


def updateSavedCookie():
    global cookie
    
    try:
        cookieFile = open("cookie.txt", "w")
        cookieFile.write(cookie)
        cookieFile.close()
    except:
        print("\033[33mSaving cookie failed.")


def getCurrentVersion():
    try:
        versionFile = open("VERSION.txt")
    except:
        return
    return versionFile.read()


def getLatestVersion():
    try:
        versionRequest = requests.get("https://api.github.com/repos/kartFr/Auto-Animation-Reuploader/releases/latest")
    except:
        return
   
    return json.loads(versionRequest.content)["name"]

def clearScreen():
    os.system("cls" if os.name == "nt" else "clear")


def updateFile():
    clearScreen()
    print("\033[33mUpdating. Please be patient.")
    try:
        dataPath = sys._MEIPASS
    except:
        dataPath = os.path.dirname(os.path.abspath(__file__)) # so i can test when not packaged
    subprocess.Popen(["Python", os.path.join(dataPath, "updater.py")])
    sys.exit()


XSRFTokenEvent = threading.Event()
fetchingXSRFToken = False
XSRFToken = None

def getXSRFToken():
    global XSRFToken
    global fetchingXSRFToken
    global XSRFTokenEvent

    if fetchingXSRFToken:
        XSRFTokenEvent.wait()
        return
    
    fetchingXSRFToken = True

    if XSRFToken:
        print(f"\033[31mXSRF token expired fetching new one")

    for i in range(3):
        try:
            XSRFToken = requests.post(
                "https://auth.roblox.com/v2/logout",
                cookies={ ".ROBLOSECURITY": cookie }
            ).headers["X-CSRF-TOKEN"]
            break
        except:
            print(f"\033[31mFailed getting XSRF token trying in 5 seconds")
            time.sleep(5)
            pass

    fetchingXSRFToken = False
    XSRFTokenEvent.set()
    XSRFTokenEvent.clear()


def getAssetData(assetid):
    try:
        request = requests.get("https://assetdelivery.roblox.com/v1/asset/?id=" + str(assetid))
    except:
        return False
    return request.content      

def publishAsset(assetTypeName, name, creatorId, isGroup, assetData):
    try:
        request =  requests.post(
            f"https://www.roblox.com/ide/publish/uploadnewanimation?assetTypeName={ assetTypeName }&name={ name }&description=kartfr🤑🤑&AllID=1&ispublic=False&allowComments=True&isGamesAsset=False{ '&groupId=' + str(creatorId) if isGroup else '' }",
            assetData,
            headers={ "X-CSRF-TOKEN": XSRFToken,  "User-Agent": "RobloxStudio/WinInet" },
            cookies={ ".ROBLOSECURITY": cookie }
        )
    except:
        pass
    return request

def publishAnimation(animationInfo, creatorId, isGroup):
    global completedAnimations
    global fetchingXSRFToken
    global idsUploaded
    global totalIds
    global XSRFToken
    global cookie

    animationId = animationInfo["id"]
    name = animationInfo["name"]
    animationCreatorId = animationInfo["creator"]["targetId"]
    assetType = animationInfo["type"]

    newAnimationId = None
    animationInfo = None
    failureReason = None
    animationData = None  

    if animationCreatorId == creatorId:
        failureReason = "Owned"

    if animationCreatorId == 1: # 1 is Roblox
        failureReason = "Roblox"

    if assetType != "Animation":
        failureReason = "Not Animation"

    for i in range(5):
        if failureReason:
            break

        if fetchingXSRFToken:
            getXSRFToken()
        
        if not animationData:
            animationData = getAssetData(animationId)
            if not animationData:
                time.sleep(1)
                continue

        publishRequest = publishAsset("Animation", name, creatorId, isGroup, animationData)

        content = publishRequest.content.decode()
        if content.isnumeric():
            newAnimationId = content
            break
        
        match publishRequest.status_code:
            case 422: #unprocessable entity
                break
            case 500: # Internal Server Error
                name = "[Censored Name]" # Even though i am detecting if the name is bad sometimes roblox likes to just give 500 internal server error instead of "innapropriate name or description"
                time.sleep(3)
                continue
            case 403: # Forbidden
                if content == "XSRF Token Validation Failed":
                    getXSRFToken()
                    continue

        match content:
            case "Inappropriate name or description.":
                name = "[Censored Name]"
            case _:
                print(f"\033[31mError found please report:\nCode: { publishRequest.status_code }\nReason: { publishRequest.reason }\nContent: { content }") #Hopefully this will be fine
                
        time.sleep(1)
    
    idsUploaded += 1
    if newAnimationId:
        print(f"\033[32m[{ idsUploaded }/{ totalIds }] { name }: { animationId } ; { newAnimationId }")
        completedAnimations[animationId] = newAnimationId
    else:
        match failureReason:
            case "Owned":
                print(f"\033[33m[{ idsUploaded }/{ totalIds }] Already own { name }: { animationId }.")
            case "Roblox":
                print(f"\033[33m[{ idsUploaded }/{ totalIds }] { name } is owned by roblox: { animationId }.")
            case "Not Animation":
                print(f"\033[33m[{ idsUploaded }/{ totalIds }] { name } is not an animation: { animationId }.")
            case _:
                print(f"\033[31m[{ idsUploaded }/{ totalIds }] Failed to publish { name }: { animationId }.")

    if idsUploaded == totalIds:
        global completedEvent
        completedEvent.set()
        completedEvent.clear()


def publishAnimationAsync(animationInfo, creatorId, isGroup):
    newThread = threading.Thread(target=publishAnimation, args=(animationInfo, creatorId, isGroup,))
    newThread.start()

    animationCreatorId = animationInfo["creator"]["targetId"]
    assetType = animationInfo["type"]

    if animationCreatorId != creatorId and animationCreatorId != 1 and assetType == "Animation": # no reason to throttle because it wont do any requests
        time.sleep(60/400) #throttle, because this is what roblox reccomends(400 a minute). Someone can pull and I will merge with your permission if its stable if you want to make it faster.


def getAssetIdInfo(assetIds):
    for i in range(5):
        try:
            assetDetailsRequest = requests.get(
                f"https://develop.roblox.com/v1/assets?assetIds={ ",".join(str(i) for i in assetIds) }",
                cookies={ 
                    ".ROBLOSECURITY": cookie 
                })
            assetInfoList = json.loads(assetDetailsRequest.content)
        except:
            time.sleep(1)
            continue

        if assetDetailsRequest.status_code == 500:
            time.sleep(1)
            continue
        
        return assetInfoList["data"]
    
    
def getMissingIds(ids, assetInfoList):
    global idsUploaded
    global totalIds

    infoListIds = {}

    for animationInfo in assetInfoList:
        infoListIds[animationInfo["id"]] = True # o(1) fart search gayatt KILL ME

    for id in ids:
        if int(id) in infoListIds:
            continue

        idsUploaded += 1
        print(f"\033[31m[{ idsUploaded }/{ totalIds }] Invalid asset id: { id }.")


def splitArray(array, size):
    return [array[i:i + size] for i in range(0, len(array), size)]


def bulkPublishAnimations(animations, creatorId, isGroup):
    global totalIds
    global completedEvent
    global finished
    global idsUploaded

    splitAnimations = splitArray(animations, 50) # max bulk get asset details is 50
    totalIds = len(animations)
    startTime = time.time()
    idsUploaded = 0

    getXSRFToken() #get xsrf for first time meow :3 I hate myself

    for animationList in splitAnimations:
        animationInfoList = getAssetIdInfo(animationList)
        getMissingIds(animationList, animationInfoList)

        for animationInfo in animationInfoList:
            publishAnimationAsync(animationInfo, creatorId, isGroup)
    
    if idsUploaded != totalIds:
        completedEvent.wait()

    hours, remainder = divmod(time.time() - startTime, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"\033[0mPublishing took { int(hours) } hours, { int(minutes) } minutes, and { int(seconds) } seconds.")
    print("\033[0mWaiting for client...")
    finished = True


def bulkPublishAnimationsAsync(animations, creatorId, isGroup):
    newThread = threading.Thread(target=bulkPublishAnimations, args=(animations, creatorId, isGroup,))
    newThread.start()


class Requests(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        global finished
        global completedAnimations

        if finished and len(completedAnimations) == 0:
            global started

            self.wfile.write(bytes(("done").encode("utf-8")))
            print("\033[0mYou may close this terminal. (You can spoof again without restarting if you need to.)")
            finished = False
            started = False
        else:
            currentAnimations = completedAnimations
            completedAnimations = {  }
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
        print("\033[33mUploading animations.")
        bulkPublishAnimationsAsync(recievedData["animations"], recievedData["creatorId"], recievedData["isGroup"]) #new thread so client isn't waiting on message back from server

    def log_message(self, *args):
        pass

if __name__ == '__main__':
    cookie = getSavedCookie()
    latestVersion = getLatestVersion()
    clearScreen()

    if (latestVersion is not None) & (getCurrentVersion()  != latestVersion): # incase sending the request to github fails.
        print("\033[33mOut of date. New update is available on github.")
        update = input("\033[0mUpdate?(y/n): ")
        
        if update == "y":
            updateFile()
        clearScreen()

    if cookie and not isValidCookie():
        print("\033[31mCookie expired.")
        cookie = None

    if not cookie:
        while True:
            cookie = input("\033[0mCookie: ")
            clearScreen()

            if isValidCookie():
                updateSavedCookie()
                break
            elif cookie.find("WARNING:-DO-NOT-SHARE-THIS.") == -1:
                print("\033[31mNo Roblox warning in cookie. Include the entire .ROBLOSECURITY warning.")
            else:
                print("\033[31mCookie is invalid.")  

    print("\033[0mlocalhost started you may start the plugin.")

    server = HTTPServer(("localhost", 6969), Requests)
    server.serve_forever()
