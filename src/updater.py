from io import BytesIO
from zipfile import ZipFile
import requests
import subprocess

if __name__ == '__main__':
    downloadRequest = requests.get("https://github.com/kartFr/Auto-Animation-Reuploader/releases/latest/download/AnimationReuploader.zip").content
    downloadData = BytesIO(downloadRequest)

    with ZipFile(downloadData, "r") as latestDownload:
        for fileName in latestDownload.namelist():
            open(fileName, "wb").write(latestDownload.open(fileName).read())

    subprocess.Popen(["Animation Reuploader.exe"])
    