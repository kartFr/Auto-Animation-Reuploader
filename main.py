from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import json
import os

animations = {}
finished = False

os.system("cls")
cookie = input("cookie: ")

csrfToken = requests.post(
    "https://auth.roblox.com/v2/logout",
    cookies={".ROBLOSECURITY": cookie}
).headers["x-csrf-token"]

os.system("cls")
groupId = input("group id leave blank and press enter if none: ")

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

        print("plugin connected starting...")

        contentLength = int(self.headers['Content-Length'])
        animationsToPublish = json.loads(self.rfile.read(contentLength).decode('utf-8'))

        for animation in animationsToPublish:
            animationData = requests.get("https://assetdelivery.roblox.com/v1/asset/?id=" + animation).content
            animationID =  requests.post(
                f"https://www.roblox.com/ide/publish/uploadnewanimation?assetTypeName=Animation&name={animationsToPublish[animation]}&description=sub to kartfr on yt🤑🤑&AllID=1&ispublic=False&allowComments=True&isGamesAsset=False" + (groupId != "" and "&groupId=" + groupId or ""),
                animationData,
                headers={"x-csrf-token": csrfToken,  "User-Agent": "RobloxStudio/WinInet"},
                cookies={".ROBLOSECURITY": cookie}
            ).content.decode("utf-8")

            animations[animation] = animationID
            print("\033[32m" + animationsToPublish[animation] + ": " + animation + " ; " + animationID)

        print("\033[0mconverted all animations waiting for client...")
        global finished
        finished = True
            
                

    def log_message(self, *args):
        pass
        
server = HTTPServer(("localhost", 6969), Requests)

os.system("cls")
print("localhost started connect the plugin")
server.serve_forever()

