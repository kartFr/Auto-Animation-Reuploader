github_repo_latest = "https://api.github.com/repos/kartFr/Auto-Animation-Reuploader/releases/latest"
asset_delivery = "https://assetdelivery.roblox.com/v1/asset/?id="
asset_info = "https://develop.roblox.com/v1/assets?assetIds="
user_info = "https://www.roblox.com/mobileapi/userinfo"
log_out = "https://auth.roblox.com/v2/logout"

def getPublishUrl(assetTypeName, name, creatorId, isGroup):
    return (
        "https://www.roblox.com/ide/publish/uploadnewanimation?"
        f"assetTypeName={ assetTypeName }"
        f"&name={ name }"
        "&description=kartfr🤑🤑"
        "&AllID=1"
        "&ispublic=False"
        "&allowComments=True"
        "&isGamesAsset=False"
        f"{ '&groupId=' + str(creatorId) if isGroup else '' }"
    )