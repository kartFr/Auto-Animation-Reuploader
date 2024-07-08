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
totalAnimations = 0
animationsUploaded = 0
canServe = True

XSRFTokenEvent = threading.Event()
fetchingXSRFToken = False
XSRFToken = None

def clearScreen():
    os.system("cls" if os.name == "nt" else "clear")

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

    for i in range(0, 3):
        try:
            XSRFToken = requests.post(
                "https://auth.roblox.com/v2/logout",
                cookies={".ROBLOSECURITY": cookie}
            ).headers["X-CSRF-TOKEN"]
            break
        except:
            print(f"\033[31mFailed getting XSRF token trying in 5 seconds")
            time.sleep(5)
            pass

    fetchingXSRFToken = False
    XSRFTokenEvent.set()
    XSRFTokenEvent.clear()

def publishAnimation(animation, name, groupId):
    global completedAnimations
    global fetchingXSRFToken
    global animationsUploaded
    global totalAnimations
    global XSRFToken
    global cookie

    animationId = False

    if not XSRFToken:
        getXSRFToken()

    for i in range(0, 3):
        if fetchingXSRFToken:
            getXSRFToken()
            
        try:
            animationData = requests.get("https://assetdelivery.roblox.com/v1/asset/?id=" + animation).content
        except:
            time.sleep(1)
            continue
    
        try:
            publishRequest =  requests.post(
                f"https://www.roblox.com/ide/publish/uploadnewanimation?assetTypeName=Animation&name={name}&description=kartfr🤑🤑&AllID=1&ispublic=False&allowComments=True&isGamesAsset=False{"&groupId=" + str(groupId) if groupId else ""}",
                animationData,
                headers={"X-CSRF-TOKEN": XSRFToken,  "User-Agent": "RobloxStudio/WinInet"},
                cookies={".ROBLOSECURITY": cookie}
            )
        except:
            time.sleep(1)
            continue
       
        content = publishRequest.content.decode("utf-8")
        if content.isnumeric():
            animationId = content
            break

        match publishRequest.status_code:
            case 500: # Internal Server Error
                time.sleep(1)
                continue
            case 403: # Forbidden
                if content == "XSRF Token Validation Failed":
                    getXSRFToken()
                    continue

        match content:
            case "Inappropriate name or description.":
                name = "[Censored Name]"
            case _:
                print(f"\033[31mError found please report:\nCode: {publishRequest.status_code}\nReason: {publishRequest.reason}\nContent: {content}") #Hopefully this will be fine
                #print(publishRequest.status_code, publishRequest.reason)

        time.sleep(1)
    animationsUploaded += 1

    if not animationId:
        print(f"\033[31m[{animationsUploaded}/{totalAnimations}] Failed to publish {name}: {animation}.")
    else:
        print(f"\033[32m[{animationsUploaded}/{totalAnimations}] {name}: {animation} ; {animationId}")
        completedAnimations[animation] = animationId

    if animationsUploaded == totalAnimations:
        global completedEvent
        completedEvent.set()
        completedEvent.clear()

def publishAnimationAsync(animation, name, groupId):
    newThread = threading.Thread(target= publishAnimation, args=(animation, name, groupId,))
    newThread.start()
    time.sleep(60/400) #throttle, because this is what roblox reccomends(400 a minute). Someone can pull and I will merge with your permission if its stable if you want to make it faster.

def bulkPublishAnimations(animations, groupId):
    global totalAnimations
    global completedEvent
    global finished

    totalAnimations = len(animations)
    startTime = time.time()

    for animation in animations:
        publishAnimationAsync(animation, animations[animation], groupId)
    
    completedEvent.wait()

    hours, remainder = divmod(time.time() - startTime, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"\033[0mPublishing took {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds.")
    print("\033[0mWaiting for client...")
    finished = True

def bulkPublishAnimationsAsync(animations, groupId):
    newThread = threading.Thread(target=bulkPublishAnimations, args=(animations, groupId,))
    newThread.start()

def isValidCookie():
    global cookie
    isLoggedIn = requests.get(
        "https://www.roblox.com/mobileapi/userinfo",
        cookies={".ROBLOSECURITY": cookie}
    )

    try:
        json.loads(isLoggedIn.content)
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
        print("\033[33mSaving cookie failed. Try running as administrator.")

def getCurrentVersion():
    try:
        versionFile = open("version.txt")
    except:
        return
    return versionFile.read()

def getLatestVersion():
    try:
        versionRequest = requests.get("https://api.github.com/repos/kartFr/Auto-Animation-Reuploader/releases/latest")
    except:
        return
    return json.loads(versionRequest.content)["name"]

def updateFile():
    clearScreen()
    print("\033[33mUpdating. Please be patient.")
    try:
        dataPath = sys._MEIPASS
    except:
        dataPath = os.path.dirname(os.path.abspath(__file__)) # so i can test when not packaged
    subprocess.Popen(["Python", os.path.join(dataPath, "updater.py")])
    sys.exit()

class Requests(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        global finished
        global completedAnimations

        if finished and len(completedAnimations) == 0:
            global canServe

            self.wfile.write(bytes(("done").encode("utf-8")))
            #print("\033[0mYou may close this terminal.")
            canServe = False
        else:
            currentAnimations = completedAnimations
            completedAnimations = {}
            self.wfile.write(bytes(json.dumps(currentAnimations).encode("utf-8")))
            

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
        bulkPublishAnimationsAsync(recievedData["animations"], recievedData["isGroup"]) #new thread so client isn't waiting on message back from server

    def log_message(self, *args):
        pass

if __name__ == '__main__':
    clearScreen()
    cookie = getSavedCookie()
    
    if getCurrentVersion() != getLatestVersion():
        print("\033[33mOut of date. New update is available on github.")
        update = input("\033[0mUpdate?(y/n): ")
        
        if update == "y":
            updateFile()
        else:
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
    while canServe:
        server.handle_request()
