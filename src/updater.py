from io import BytesIO
from zipfile import ZipFile
import requests
import subprocess

if __name__ == '__main__':
    downloadRequest = requests.get("https://github.com/kartFr/Auto-Animation-Reuploader/releases/latest/download/AnimationReuploader.zip").content
    downloadData = BytesIO(downloadRequest)

    fileNames = []

    with ZipFile(downloadData, "r") as latestDownload:
        for fileName in latestDownload.namelist():
            fileNames.append(fileName)

    for i in range(len(fileNames)): # so the exe is guaranteed to update first, to avoid version.txt being updated and not the exe being updated kind of stupid
        fileName = fileNames[i]

        if fileName == "Animation Reuploader.exe":
            open(fileName, "wb").write(latestDownload.open(fileName).read())
            fileNames.pop(i)
            break
    
    for fileName in fileNames:
        open(fileName, "wb").write(latestDownload.open(fileName).read())

    subprocess.Popen(["Animation Reuploader.exe"])
    