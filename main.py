try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re
import config

key = config.key

# kann bis zu 100 Summaries gleichzeitig abgreifen
# dictionary mit den IDS als Key und value nen dictionary mit name visibility etc
def getPlayerSummary(steamIdList):
	playerDict = {}
	commaSeparatedList = ','.join(str(x) for x in steamIdList)
	f = urllib2.urlopen("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key="+ str(key)+"&steamids="+ commaSeparatedList)

	data = json.load(f)
	playerList = data["response"]["players"]
	for player in playerList:
		personalDict = {}
		if "realname" in player:
			personalDict["realname"] = player["realname"]
		personalDict["visibility"] = player["communityvisibilitystate"]
		personalDict["timecreated"] = player["timecreated"]
		if "loccityid" in player:
			personalDict["loccityid"] = player["loccityid"]
		if "locstatecode" in player:
			personalDict["locstatecode"] = player["locstatecode"]
		if "loccountrycode" in player:
			personalDict["loccountrycode"] = player["loccountrycode"]
		if "locstatecode" in player:
			personalDict["locstatecode"] = player["locstatecode"]

		playerDict[player["steamid"]] = personalDict

	return playerDict

def removeNonAscii(s): 
	return "".join(i for i in s if ord(i)<128)

def getFriends(steamId):
	friends = []
	try:
		f = urllib2.urlopen("http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key="+ str(key)+"&steamid="+ str(steamId) +"&relationship=friend")
		data = json.load(f)
		friendsList = data["friendslist"]["friends"]
		for friend in friendsList:
			friends.append(str(friend["steamid"]))
	except:
		print("Private SteamId: ", steamId)
		pass
	return friends

def getPlayerAchievements(steamId, gameId):
	achievements = {}
	try:
		f = urllib2.urlopen("http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid="+ str(gameId) +"&key="+ str(key) +"&steamid=" + str(steamId))
		data = json.load(f)
		allAchievements = data["playerstats"]["achievements"]
		print (data["playerstats"]["gameName"])
		for achievement in allAchievements:
			achievements[str(achievement["apiname"])] = achievement["achieved"]
	except:
		pass
	return achievements

def getOwnedGames(steamId):
	games = []
	f = urllib2.urlopen("http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key="+ str(key) +"&steamid=" + str(steamId) + "&format=json")
	data = json.load(f)
	gameList = data["response"]["games"]
	for game in gameList:
		games.append((game["appid"], game["playtime_forever"]))
	return games

def getGlobalAchievementsPercentage(gameId):
	globalPercentages = {}
	f = urllib2.urlopen("http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid="+ str(gameId) +"&format=json")
	data = json.load(f)
	percentages = data["achievementpercentages"]["achievements"]
	for achievement in percentages:
		if not achievement["percent"] > 100:
			globalPercentages[str(achievement["name"])] = achievement["percent"]
	return globalPercentages

def achievementScore(globalAchievements, playerAchievements):
	score = float(0.0)
	for achievement in globalAchievements:
		score -= (float(globalAchievements[achievement]) / 100)
	for achievement in playerAchievements:
		score += playerAchievements[achievement]
	return score

def getUrl(url):
	try:
		req = urllib2.Request(url, headers={'User-Agent' : "Magic Browser"}) 
		f = urllib2.urlopen(req)
		return f
	except:
		print ("Error in URL")
		return ""

def getUserTags(gameId):
	tags = []
	output = getUrl("http://store.steampowered.com/app/"+str(gameId)).read()
	p = re.compile('<a href="http://store.steampowered.com/tag/.*?\n.*?\n')
	m = p.findall(output)
	for tag in m:
		tags.append(removeNonAscii(tag.split("\n")[1].replace("\t", "").split("<")[0]))
	return tags 

def getGameName(gameId):
	output = getUrl("http://store.steampowered.com/app/"+str(gameId)).read()
	p = re.compile('<div class="apphub_AppName">.*?</div>')
	m = p.findall(output)
	if m:
		return removeNonAscii(m[0].split('">')[1].split("</")[0])
	else:
		return "-- Not found --"



# DB Played : UserID, GameID, AchievementSumme, Spieldauer
# CREATE TABLE played ( userId int, gameId int, achievementSum int, playTime int);
# DB Games  : GameID, GameTags, GlobalAchievementSumme
# CREATE TABLE games ( gameId int, gameTags varchar(255), globalAchievementSum int);
# DB Friends: UserID, UserID
# CREATE TABLE friends ( userId1 int, userId2 int);

# Ulrich, meine, svens, Luux
import time
myList = [76561198020163289, 76561198100742438, 76561198026036441, 76561198035162874]

print getPlayerSummary(myList)
# ownedGames = getOwnedGames(myList[3])

# counter = 0
# print (len(ownedGames))
# for game in ownedGames:
# 	gameId = game[0]
# 	playTime = game[1]
# 	time3 = time.time()
# 	globalAchievements = getGlobalAchievementsPercentage(gameId)
# 	playerAchievements = getPlayerAchievements(myList[0], gameId)
# 	time4 = time.time()
# 	print (achievementScore(globalAchievements, playerAchievements), gameId, str(playTime) + " min")
# 	print (getUserTags(gameId), getGameName(gameId))
# 	time5 = time.time()
# 	print ("\t AchievementTime: ", time4-time3, "s")
# 	print ("\t Steamstore Time: ", time5-time4, "s")