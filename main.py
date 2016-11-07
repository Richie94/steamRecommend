try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re
import config
import pymysql
from datetime import datetime
from random import choice

key = config.key

#checks if attribute is in array and returns it, else return empty string
def inArray(attribute, array):
	if attribute in array:
		return array[attribute]
	else:
		return ""

# Up to 100 summarys in parallel
# returns: dictionary with ids as a key and with dictionary in value field for all necessary information
def getPlayerSummary(steamIdList):
	playerDict = {}
	for i in range(len(steamIdList)/100):
		partialList = steamIdList[i*100:(i+1)*100]
		commaSeparatedList = ','.join(str(x) for x in partialList)
		f = urllib2.urlopen("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key="+ str(key)+"&steamids="+ commaSeparatedList)
		data = json.load(f)
		playerList = data["response"]["players"]
		for player in playerList:
			personalDict = {}
			personalDict["realname"] = inArray("realname", player)
			personalDict["visibility"] = inArray("communityvisibilitystate", player)
			personalDict["timecreated"] = inArray("timecreated", player)
			personalDict["loccityid"] = inArray("loccityid", player)
			personalDict["locstatecode"] = inArray("locstatecode", player)
			personalDict["loccountrycode"] = inArray("loccountrycode", player)
			playerDict[player["steamid"]] = personalDict
	return playerDict

def removeNonAscii(s): 
	return "".join(i for i in s if ord(i)<128)

def getFriends(steamId):
	friendDict = {}
	try:
		f = urllib2.urlopen("http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key="+ str(key)+"&steamid="+ str(steamId) +"&relationship=friend")
		data = json.load(f)
		friendsList = data["friendslist"]["friends"]
		for friend in friendsList:
			if "steamid" in friend:
				personalDict = {}
				personalDict["relationship"] = friend["relationship"]
				personalDict["friendsSince"] = friend["friend_since"]
				friendDict[friend["steamid"]] = personalDict
	except urllib2.HTTPError:
		#Private profiles possible
		pass
	return friendDict

def getPlayerAchievements(steamId, gameId):
	achievements = {}
	try:
		f = urllib2.urlopen("http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid="+ str(gameId) +"&key="+ str(key) +"&steamid=" + str(steamId))
		data = json.load(f)
		allAchievements = inArray("achievements", data["playerstats"])
		#print (data["playerstats"]["gameName"])
		for achievement in allAchievements:
			achievements[str(achievement["apiname"])] = achievement["achieved"]
	except urllib2.HTTPError:
		# Not every time stats available
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

def getUserListFromDB(cursor):
	cursor.execute("SELECT steamid FROM user")
	userList = cursor.fetchall()
	return [user["steamid"] for user in userList]


def addFriendsToUser(userId, friends, cursor):
	print "\tAdd friends to User in database"
	for friend in friends:
		friendId, relationship, friendsSince = str(friend), str(friends[friend]["relationship"]), str(friends[friend]["friendsSince"])
		try:
			cursor.execute("INSERT INTO `user_friends` (`steamid`,`friendsteamid`,`relationship`,`friendsSince`) VALUES ('"+userId+"', '"+ friendId +"', '"+ relationship +"', '"+ friendsSince +"');")
		except pymysql.err.IntegrityError:
			# if we override something
			pass
	return 1

def addUserSummarys(userList, cursor):
	print "\tAdd User Summaries (" + str(len(userList)) + ")" 
	now = datetime.now()
	playerSummaries = getPlayerSummary(userList)
	print "\tLoaded Player Summaries - Start upload to database"
	for summary in playerSummaries:
		curSum = playerSummaries[summary]
		steamid, visibility, realname, timecreated = str(summary), str(curSum["visibility"]), removeNonAscii(curSum["realname"].replace("'","")), str(curSum["timecreated"])
		loccountrycode, locstatecode, loccityid = str(curSum["loccountrycode"]), str(curSum["locstatecode"]), str(curSum["loccityid"])
		currentTime = now.strftime("%Y-%m-%d %H:%M")
		try:
			cursor.execute("INSERT INTO `user`(`steamid`,`visibility`,`realname`,`timecreated`,`loccountrycode`,`locstatecode`,`cityid`,`lastUpdated` ) VALUES ('"+steamid+"', '"+visibility+"', '"+realname+"', '"+timecreated+"', '"+loccountrycode+"', '"+locstatecode+"', '"+loccityid+"', '"+currentTime+"');")
		except pymysql.err.IntegrityError:
			# if we override something
			pass
	return 1

# actionCounter counts calls to steam API
def crawlUserIDsViaFriends(cursor, limitCounter=10000):
	actionCounter = 0
	userList = getUserListFromDB(cursor)
	#start with random user
	currentUser = choice(userList)
	while actionCounter < limitCounter:
		print("Action: " + str(actionCounter) + " - CurrentUser: " + str(currentUser))
		# 1. get Friends from User (1x call)
		userFriends = getFriends(currentUser)
		print "\tLoaded friendlist"
		friendList = [str(user) for user in userFriends]
		actionCounter += 1
		# 2. add their summarys (max 100 summarys per call)
		addUserSummarys(friendList, cursor)
		actionCounter += 1
		# 3. add them to friendslist
		addFriendsToUser(currentUser, userFriends, cursor)
		# 4. take random friend as starting point, if no friend findable take random user
		if len(userFriends.keys()) > 1:
			currentUser = choice(friendList)	
		else:
			currentUser = choice(getUserListFromDB(cursor))



connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

# Ulrich, meine, svens, Luux
myList = [76561198020163289, 76561198100742438, 76561198026036441, 76561198035162874]

#cursor.execute("SELECT * FROM user_friends")
#print(len(cursor.fetchall()))
crawlUserIDsViaFriends(cursor, 100)
#print getUserListFromDB(cursor)


#ownedGames = getOwnedGames(myList[3])

# counter = 0
# print (len(ownedGames))
#for game in ownedGames:
 	#gameId = game[0]
 	#playTime = game[1]
	#globalAchievements = getGlobalAchievementsPercentage(gameId)
	#print(myList[0], gameId)
 	#playerAchievements = getPlayerAchievements(myList[0], gameId)
	#print (achievementScore(globalAchievements, playerAchievements), gameId, str(playTime) + " min")
	#print (getUserTags(gameId), getGameName(gameId))
cursor.close()
connection.close()