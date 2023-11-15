local HTTPService = game:GetService("HttpService")
local MarketPlaceService = game:GetService("MarketplaceService")

local gui = script.Parent.Frame
local started = false
local toolbar = plugin:CreateToolbar("Animation Spoofer")
local pluginButton = toolbar:CreateButton("Spoof Animations", "Launch the python script first", "http://www.roblox.com/asset/?id=15351873604")

local widget = plugin:CreateDockWidgetPluginGui(
	"spoofer",
	DockWidgetPluginGuiInfo.new(
		Enum.InitialDockState.Float,
		false,
		false,
		200,
		100,
		200,
		100
	)
)

widget.Title = "KARTFR ANIM WWWWWWWWWW FAT FART XDXDXD"

script.Parent.Parent = widget

pluginButton.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)

gui.BUTTon.MouseButton1Down:Connect(function()
	if started then
		return
	end

	local success, results = pcall(function()
		HTTPService:GetAsync("http://localhost:6969")
	end)

	if not success then
		warn("start the python script")

		return
	end

	started = true
    
	local animations = {}
	local animationMap = {}
	local skipped = {}
	local animationCount = 0

	warn("connected to local host starting...")

	for i, v in ipairs(game:GetDescendants()) do
		if v:IsA("Animation") then
			local id = string.gsub(v.AnimationId, "%D", "")

			if id == "" or id == "0" then
				continue
			end

			if animations[id] then
				table.insert(animationMap[id], v)
				continue
			end

			local name

			for i=1,3 do
				pcall(function()
					name = MarketPlaceService:GetProductInfo(id).Name
				end)

				if name then
					break
				else
					if i == 3 then
						warn(v, "error getting product info from " .. id .. " skipping...")
						table.insert(skipped, v)
					else
						warn(v, "error getting product info from " .. id .. " retrying in 1 seconds...")
						task.wait(1)
					end
				end
			end

			if name then
				animations[id] = name
				animationMap[id] = {}
				animationCount += 1
				
				table.insert(animationMap[id], v)
				warn("looped through " .. animationCount .. " different animations")
			end
		end
	end
	warn("skipped animations: ", table.unpack(skipped))
	warn("sending " .. animationCount .. " animations to upload")
	HTTPService:PostAsync("http://localhost:6969", HTTPService:JSONEncode(animations))
	warn("sent animations to publish")


	local newAnimations = ""
	
	repeat 
		task.wait(1) 
		newAnimations = HTTPService:GetAsync("http://localhost:6969")
	until newAnimations ~= ""

	newAnimations = HTTPService:JSONDecode(newAnimations)
	
	local failedAnimations = {}

	for oldId, newId in pairs(newAnimations) do
		for i, animation in pairs(animationMap[oldId]) do
			animation.AnimationId = "rbxassetid://" .. newId
			print(animation, "Id changed to " .. newId)
		end
		animationMap[oldId] = nil
	end
	
	for i,v in pairs(animationMap) do
		for i, failedAnimation in pairs(v) do
			table.insert(failedAnimations, failedAnimation)
		end
	end
	
	warn("failed to steal animations for:", table.unpack(failedAnimations))
	started = false
end)
