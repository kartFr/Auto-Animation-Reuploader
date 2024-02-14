from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import threading
import time
import requests
import json
import os

start = 0
animations = {}
finished = False
started = False

def makeAnimations(animationsToPublish):
    global xsrf
    global start
    start = time.time()
    count = 0
    maxCount = len(animationsToPublish)

    print("plugin connected started publishing...")


    for animation in animationsToPublish:
        count += 1

        for i in range(0, 3):
            animationData = requests.get("https://assetdelivery.roblox.com/v1/asset/?id=" + animation).content
            publishRequest =  requests.post(
                f"https://www.roblox.com/ide/publish/uploadnewanimation?assetTypeName=Animation&name={animationsToPublish[animation]}&description=sub to kartfr on yt🤑🤑&AllID=1&ispublic=False&allowComments=True&isGamesAsset=False" + (groupId != "" and "&groupId=" + groupId or ""),
                animationData,
                headers={"X-CSRF-TOKEN": xsrf,  "User-Agent": "RobloxStudio/WinInet"},
                cookies={".ROBLOSECURITY": cookie}
            )

            animationID = publishRequest.content.decode("utf-8")

            if animationID.isnumeric():
                break
            else:
                print(f"\033[31m[{count}/{maxCount}] failed to publish failed to publish {animationsToPublish[animation]} with {animation} retrying in 3 seconds")
                time.sleep(3)

                if publishRequest.status_code == 403 and publishRequest.reason == "XSRF Token Validation Failed":
                    print(f"\033[31mXSRF token expired fetching new one")
                    for i in range(0, 3):
                            try:
                                xsrf = requests.post(
                                    "https://auth.roblox.com/v2/logout",
                                    cookies={".ROBLOSECURITY": cookie}
                                ).headers["X-CSRF-TOKEN"]

                                break
                            except:
                                print(f"\033[31mFailed getting XSRF token trying in 3 seconds")
                                time.sleep(3)

        if animationID.isnumeric():
            animations[animation] = animationID
            print(f"\033[32m[{count}/{maxCount}] {animationsToPublish[animation]}: {animation} ; {animationID}")
        else:
            print(f"\033[31m[{count}/{maxCount}] failed to publish {animationsToPublish[animation]} with {animation}")
    
    hours, remainder = divmod(time.time() - start, 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"\033[0mpublishing took {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds")
    print("\033[0mconverted all animations waiting for client...")
    global finished
    finished = True

class Requests(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        if finished:
            self.wfile.write(bytes(json.dumps(animations).encode("utf-8")))
            print("sending new ID's to client you can exit the terminal now")
            

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        if not started:
            started = True
            contentLength = int(self.headers['Content-Length'])
            animationsToPublish = json.loads(self.rfile.read(contentLength).decode('utf-8'))
    
            thread = threading.Thread(target=makeAnimations, args=[animationsToPublish])
            thread.start()     

    def log_message(self, *args):
        pass
        
server = HTTPServer(("localhost", 6969), Requests)

os.system("cls")
cookie = input("cookie: ")

xsrf = requests.post(
    "https://auth.roblox.com/v2/logout",
    cookies={".ROBLOSECURITY": cookie}
).headers["X-CSRF-TOKEN"]

os.system("cls")
groupId = input("group id leave blank and press enter if none: ")

os.system("cls")
print("localhost started connect the plugin")
server.serve_forever()
