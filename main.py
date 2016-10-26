from urllib2 import urlopen, Request
import MySQLdb
import json, re

import config

key = config.key

def getFriends(steamId):
	friends = []
	try:
		f = urlopen("http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key="+ str(key)+"&steamid="+ str(steamId) +"&relationship=friend")
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
		f = urlopen("http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid="+ str(gameId) +"&key="+ str(key) +"&steamid=" + str(steamId))
		data = json.load(f)
		allAchievements = data["playerstats"]["achievements"]
		for achievement in allAchievements:
			achievements[str(achievement["apiname"])] = achievement["achieved"]
	except:
		pass
	return achievements

def getOwnedGames(steamId):
	games = []
	f = urlopen("http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key="+ str(key) +"&steamid=" + str(steamId) + "&format=json")
	data = json.load(f)
	gameList = data["response"]["games"]
	for game in gameList:
		games.append((game["appid"], game["playtime_forever"]))
	return games

def getGlobalAchievementsPercentage(gameId):
	globalPercentages = {}
	f = urlopen("http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/?gameid="+ str(gameId) +"&format=json")
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
		req = Request(url, headers={'User-Agent' : "Magic Browser"}) 
		f = urlopen(req)
		return f
	except:
		print "Error in URL"
		return ""

def getUserTags(gameId):
	tags = []
	output = getUrl("http://store.steampowered.com/app/"+str(gameId)).read()
	p = re.compile('<a href="http://store.steampowered.com/tag/.*?\n.*?\n')
	m = p.findall(output)
	for tag in m:
		tags.append(tag.split("\n")[1].replace("\t", "").split("<")[0])
	return tags 

def getGameName(gameId):
	output = getUrl("http://store.steampowered.com/app/"+str(gameId)).read()
	p = re.compile('<div class="apphub_AppName">.*?</div>')
	m = p.findall(output)
	name = m[0].split('">')[1].split("</")[0]
	return name 


# DB Played : UserID, GameID, AchievementSumme, Spieldauer
# CREATE TABLE played ( userId int, gameId int, achievementSum int, playTime int);
# DB Games  : GameID, GameTags, GlobalAchievementSumme
# CREATE TABLE games ( gameId int, gameTags varchar(255), globalAchievementSum int);
# DB Friends: UserID, UserID
# CREATE TABLE friends ( userId1 int, userId2 int);

# Ulrich, meine, svens
myList = [76561198020163289, 76561198100742438, 76561198026036441]
ownedGames = getOwnedGames(myList[2])
counter = 0
print len(ownedGames)
for game in ownedGames:
	gameId = game[0]
	playTime = game[1]
	#counter += playTime
	#print counter/(60*24)
	globalAchievements = getGlobalAchievementsPercentage(gameId)
	playerAchievements = getPlayerAchievements(myList[0], gameId)
	print achievementScore(globalAchievements, playerAchievements), gameId, str(playTime) + " min" , getUserTags(gameId), getGameName(gameId)
	#counter += 1
	#if counter > 10:
	#	break