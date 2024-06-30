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
import threading
import requests
import json
import time
import os

completedEvent = threading.Event()
completedAnimations = {}
started = False
finished = False
cookie = None
totalAnimations = 0
animationsUploaded = 0

XSRFTokenEvent = threading.Event()
fetchingXSRFToken = False
XSRFToken = None

def clearScreen():
    os.system("cls" if os.name == "nt" else "clear") #nt is windows, clear is for linux and mac. (this is the only mac and linux incompatibility in the previous versions that I was too lazy to fix lmao)

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

    animationId = None

    if not XSRFToken:
        getXSRFToken()

    for i in range(0, 3):
        if fetchingXSRFToken:
            getXSRFToken()

        animationData = None
        publishRequest = None

        try:
            animationData = requests.get("https://assetdelivery.roblox.com/v1/asset/?id=" + animation).content
        except:
            continue
        
        try:
            publishRequest =  requests.post(
                f"https://www.roblox.com/ide/publish/uploadnewanimation?assetTypeName=Animation&name={name}&description=kartfr🤑🤑&AllID=1&ispublic=False&allowComments=True&isGamesAsset=False{"&groupId=" + str(groupId) if groupId else ""}",
                animationData,
                headers={"X-CSRF-TOKEN": XSRFToken,  "User-Agent": "RobloxStudio/WinInet"},
                cookies={".ROBLOSECURITY": cookie}
            )
        except:
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
                if publishRequest.reason == "XSRF Token Validation Failed":
                    getXSRFToken()
                    continue

        match content:
            case "Inappropriate name or description.":
                name = "[Censored Name]"
            case _:
                print(f"\033[31mError found please report: {content}") #Hopefully this will be fine
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
    time.sleep(1/7) #throttle(420 a minute XDXD) because bad things happen when you are sending too many requests at once without a proxy. Someone can pull and I will merge with your permission if you want to make it faster.
    #I left 80 for some room for errors. Should be fine as long as you don't have more than 80 animations failing within a minute.

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

class Requests(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        global finished
        global completedAnimations

        if finished and len(completedAnimations) == 0:
            self.wfile.write(bytes(("done").encode("utf-8")))
            print("\033[0mYou may close this terminal.")
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
    
clearScreen()
cookie = input("Cookie: ")
clearScreen()

print("localhost started you may start the plugin.")
server = HTTPServer(("localhost", 6969), Requests)
server.serve_forever()
