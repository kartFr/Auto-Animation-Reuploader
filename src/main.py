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

import subprocess, endpoints, requests, aiohttp, asyncio, json, time, sys, os, uvicorn
from fastapi.responses import JSONResponse, Response
from fastapi import FastAPI, Request

completedAnimations = {}
XSRFToken = None
started = False
finished = False
cookie = None
totalIds = 0
idsUploaded = 0

app = FastAPI()

class Config:
    cookie_file = "cookie.txt"
    version_file = "VERSION.txt"
    server_port = 5544


async def sendRequestAsync(session, requestType, url, cookies={}, headers={}, data=None):
    global XSRFToken
    headers = {i: v for i, v in headers.items() if v is not None}

    for i in range(2):
        try:
            async with getattr(session, requestType)(
                url,
                data=data,
                headers=headers,
                cookies=cookies
            ) as response:
                if response.status == 403: # forbidden(bad xsrf)
                    XSRFToken = response.headers.get("x-csrf-token")
                    headers["X-CSRF-TOKEN"] = XSRFToken
                    continue
                return {"status_code": response.status, "reason": response.reason, "content": await response.read()}
        except:
            pass
            
def isValidCookie():
    global cookie
    
    try:
        response = json.loads(requests.get(
            endpoints.authenticated,
            cookies={".ROBLOSECURITY": cookie}
        ).content)

        if "errors" in response:
            return False
        return True
    except:
        return False

def getSavedCookie():
    try:
        with open(Config.cookie_file) as cookieFile:
            return cookieFile.read()
    except:
        return


def updateSavedCookie():
    global cookie
    
    try:
        with open("cookie.txt", "w") as cookieFile:
            cookieFile.write(cookie)
    except:
        print("\033[33mSaving cookie failed.")


def getCurrentVersion():
    try:
        with open(Config.version_file) as versionFile:
            return versionFile.read().strip()
    except:
        return


def getLatestVersion():
    try:
        versionResponse = requests.get(endpoints.github_repo_latest)
        return json.loads(versionResponse.content)["name"]
    except:
        return


def clearScreen():
    os.system("cls" if os.name == "nt" else "clear")


def updateFile():
    clearScreen()
    print("\033[33mUpdating. Please be patient.")
    dataPath = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    subprocess.Popen(["Python", os.path.join(dataPath, "updater.py")])
    sys.exit()


async def publishAssetAsync(session, oldId, name, creatorId, isGroup):
    global completedAnimations, XSRFToken, cookie, idsUploaded
    newAnimationId = None
    animationData = None  
        
    for i in range(3):

        if not animationData:
            try:
                dataResponse = await sendRequestAsync(session, "get", endpoints.asset_delivery + str(oldId))
                animationData = dataResponse["content"]
            except:
                await asyncio.sleep(1)
                continue

        publishRequest = await sendRequestAsync(
            session,
            "post",
            endpoints.getPublishUrl("Animation", name, creatorId, isGroup),
            cookies={ ".ROBLOSECURITY": cookie },
            headers={ "X-CSRF-TOKEN": XSRFToken,  "User-Agent": "RobloxStudio/WinInet" },
            data=animationData
        )

        if publishRequest is None:
            await asyncio.sleep(1)
            continue

        content = publishRequest["content"].decode()
        if content.isnumeric():
            newAnimationId = content
            break

        match publishRequest["status_code"]:
            case 500 | 400 | 422: # Bad Request / Internal Server Error / Unprocessable Entity
                name = "[Censored Name]" # Even though i am detecting if the name is bad sometimes roblox likes to just give other shit
                await asyncio.sleep(1)
                continue
            case 403 | 504 | 502: # unauthorized(bad xsrf) / gateway timeout(bad wifi XDXDXDDDDD fat noobs KILLL MEE) / bad gateway 
                await asyncio.sleep(2**i+1)
                continue

        match content:
            case "Inappropriate name or description.":
                name = "[Censored Name]"
            case _:
                print(f"\033[31mError found please report:\nCode: { publishRequest['status_code'] }\nReason: { publishRequest['reason'] }\nContent: { content }") #Hopefully this will be fine
        await asyncio.sleep(1)

    idsUploaded += 1
    if newAnimationId:
        print(f"\033[32m[{ idsUploaded }/{ totalIds }] { name }: { oldId } ; { newAnimationId }")
        completedAnimations[oldId] = newAnimationId
    else:    
        print(f"\033[31m[{ idsUploaded }/{ totalIds }] Failed to publish { name }: { oldId }.")


async def closeSessionWhenTasksAreFinished(session, tasks):
    await asyncio.gather(*tasks)
    await session.close()


def splitArray(array, size):
    return [array[i:i + size] for i in range(0, len(array), size)]


async def getBulkAssetInfo(session, assetIds):
    while True: # we will see how bad this will go lol
        try:
            assetInfoResponse = await sendRequestAsync(
                session, 
                "get", 
                endpoints.asset_info + ",".join(str(i) for i in assetIds),
                { ".ROBLOSECURITY": cookie }
            )

            return json.loads(assetInfoResponse["content"])["data"]
        except:
            await asyncio.sleep(5)
            continue


def doesIndexExistInArray(array, index):
    try:
        array[index]
        return True
    except:
        return False


async def bulkPublishAssetsAsync(assetType, ids, creatorId, isGroup):
    global finished, totalIds, idsUploaded
    splitAssetIds = splitArray(ids, 50) # max bulk get asset details is 50
    totalIds = len(ids)
    idsUploaded = 0
    startTime = time.time() # time.time truly peak code meow :3 I hate myself
    sessionTasks = []
    getAssetInfoTask = None
    getAssetInfoSession = aiohttp.ClientSession() # cus i don't feel that comfortable reusing sessions meant for uploading to get asset info
    index = 0

    for assetIds in splitAssetIds:
        session = aiohttp.ClientSession()
        uploadTasks = []

        if getAssetInfoTask is None:
            assetInfoList = await getBulkAssetInfo(getAssetInfoSession, assetIds)
        else:
            if getAssetInfoTask.done():
                assetInfoList = getAssetInfoTask.result()
            else:
                assetInfoList = await getAssetInfoTask

        if doesIndexExistInArray(splitAssetIds, index + 1):
            getAssetInfoTask = asyncio.create_task(getBulkAssetInfo(getAssetInfoSession, splitAssetIds[index + 1])) #get the next asset info so there isn't that much of a wait next index
        
        missingIds = len(assetIds) - len(assetInfoList)
        if missingIds != 0:
            print(f"\033[33mSkipping {missingIds} ids. (Invalid ids)") # for bad ids or whatever
            idsUploaded += missingIds
        
        for assetInfo in assetInfoList:
            targetCreatorId = assetInfo["creator"]["targetId"]
            assetId = assetInfo["id"]
            name = assetInfo["name"]

            if targetCreatorId == creatorId:
                idsUploaded += 1
                print(f"\033[33m[{ idsUploaded }/{ totalIds }] Already own { name }: { assetId }.")
                continue
            elif targetCreatorId == 1: # 1 is Roblox
                idsUploaded += 1
                print(f"\033[33m[{ idsUploaded }/{ totalIds }] { name } is owned by roblox: { assetId }.")
                continue
            elif assetInfo["type"] != assetType:
                idsUploaded += 1
                print(f"\033[33m[{ idsUploaded }/{ totalIds }] { name } is not an animation: { assetId }.")
                continue

            uploadTasks.append(asyncio.create_task(publishAssetAsync(session, assetId, name, creatorId, isGroup)))
            await asyncio.sleep(60/400) #throttle, because this is what roblox reccomends(400 a minute).
        sessionTasks.append(asyncio.create_task(closeSessionWhenTasksAreFinished(session, uploadTasks)))
        index += 1

    await asyncio.gather(*sessionTasks)
    await getAssetInfoSession.close()

    hours, remainder = divmod(time.time() - startTime, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"\033[0mPublishing took { int(hours) } hours, { int(minutes) } minutes, and { int(seconds) } seconds.")
    print("\033[0mWaiting for client to finish changing ids...")
    finished = True

@app.get("/")
async def get():
    global finished, completedAnimations

    if finished and len(completedAnimations) == 0:
        global started

        if started: # only print if plugin actually uplaods
            print("\033[0mYou may close this terminal. (You can spoof again without restarting if you need to.)")

        finished = False
        started = False

        return Response("done")
    else:
        currentAnimations = completedAnimations
        completedAnimations = {}
        return JSONResponse(currentAnimations)


@app.post("/")
async def post(request: Request):
    global started
    if started:
        return
    
    content = await request.json()

    if "uploadType" in content and "ids" in content and "creatorId" in content and "isGroup" in content:
        clearScreen()
        started = True
        print(f"\033[33mUploading {content['uploadType']}s.")
        asyncio.create_task(bulkPublishAssetsAsync(content["uploadType"], content["ids"], content["creatorId"], content["isGroup"]))
    else:
        global finished
        finished = True
        print("\033[31mMissing data, your plugin may be out of date. Aborting reupload.")


if __name__ == '__main__':
    cookie = getSavedCookie()
    latestVersion = getLatestVersion()
    clearScreen()

    if (latestVersion := getLatestVersion()) and (getCurrentVersion() != latestVersion):
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
            elif not "WARNING:-DO-NOT-SHARE-THIS." in cookie:
                print("\033[31mNo Roblox warning in cookie. Include the entire .ROBLOSECURITY warning.")
            else:
                print("\033[31mCookie is invalid.")  

    print("\033[0mlocalhost started you may start the plugin.")
    uvicorn.run(app, port=Config.server_port, log_level="warning")
