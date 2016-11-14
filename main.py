try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re, sys
import config
import pymysql
from datetime import datetime
from random import choice
from math import ceil
import requests

key = config.key

def progressBar(progress):
	sys.stdout.write("\r%d%%" % progress)
	sys.stdout.flush()

#checks if attribute is in array and returns it, else return empty string
def inArray(attribute, array, ourType="str"):
	if attribute in array:
		return array[attribute]
	else:
		if ourType == "int":
			return 0
		else:
			return ""

# Up to 100 summarys in parallel
# returns: dictionary with ids as a key and with dictionary in value field for all necessary information
def getPlayerSummary(steamIdList):
	playerDict = {}
	for i in range(int(ceil(float(len(steamIdList))/100.0))):
		partialList = steamIdList[i*100:(i+1)*100]
		commaSeparatedList = ','.join(str(x) for x in partialList)
		f = urllib2.urlopen("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key="+ str(key)+"&steamids="+ commaSeparatedList)
		data = json.load(f)
		playerList = data["response"]["players"]
		for player in playerList:
			personalDict = {}
			personalDict["realname"] = inArray("realname", player)
			personalDict["visibility"] = inArray("communityvisibilitystate", player)
			personalDict["timecreated"] = inArray("timecreated", player, "int")
			personalDict["loccityid"] = inArray("loccityid", player, "int")
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
		friendsList = inArray("friends",inArray("friendslist", data))
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
	gameList = inArray("games",inArray("response", data))
	for game in gameList:
		gameId = inArray("appid", game)
		playtimeForever = inArray("playtime_forever", game)
		playtime2Weeks = inArray("playtime_2weeks", game, "int")
		games.append((gameId, playtimeForever, playtime2Weeks))
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
	cookies = {'birthtime': '568022401'}
	output = requests.get("http://store.steampowered.com/app/"+str(gameId), cookies=cookies).content
	p = re.compile('<a href="http://store.steampowered.com/tag/.*?</a>',re.DOTALL)
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
	cursor.execute("SELECT steamid FROM user;")
	userList = cursor.fetchall()
	return [user["steamid"] for user in userList]

def getUsersWithoutGamesFromDB(limit, offset=0):
	cursor.execute("SELECT steamid FROM user where gameListLoaded = 0 and visibility = 3;")
	userList = cursor.fetchall()[offset:offset+limit]
	return [user["steamid"] for user in userList]


def getAllApps():
	appDict = {}
	f = urllib2.urlopen("http://api.steampowered.com/ISteamApps/GetAppList/v0001/")
	data = json.load(f)
	appList = inArray("app",inArray("apps",inArray("applist", data)))
	for app in appList:
		appid = inArray("appid", app)
		name = inArray("name", app)
		appDict[appid] = name
	return appDict


#
# Skip Achievement score so far, first collect user games, 
# then fill gamelist with gobal stats and then later compute achievementscore
#
def addUserGames(userList,cursor):
	actionCounter = 0
	for user in userList:
		print("Add games to user "+ str(user))
		query = "INSERT INTO `user_games` (`steamid`,`gameid`,`timetwoweeks`,`timeforever`) VALUES (%s,%s,%s,%s)"
		queryData = []
		gameList = getOwnedGames(user)
		actionCounter += 1
		for game in gameList:
			gameId = game[0]
			playtimeForever = game[1]
			playtime2Weeks = game[2]
			queryData.append((user, gameId, playtime2Weeks, playtimeForever))
		try:
			cursor.executemany(query, queryData)
		except pymysql.err.IntegrityError:
			# if we override something
			pass
		# set gameListLoaded Flag
		cursor.execute("UPDATE user SET gameListLoaded = 1 where steamid='"+user+"';")
	return actionCounter

def addFriendsToUser(userId, friends, cursor):
	print "\tAdd friends to User in database", 
	query = "INSERT INTO `user_friends` (`steamid`,`friendsteamid`,`relationship`,`friendsSince`) VALUES (%s,%s,%s,%s)"
	queryData = []
	for friend in friends:
		friendId, relationship, friendsSince = str(friend), str(friends[friend]["relationship"]), str(friends[friend]["friendsSince"])
		queryData.append((userId, friendId, relationship, friendsSince))
	try:
		cursor.executemany(query, queryData)
	except pymysql.err.IntegrityError:
		# if we override something
		pass
	print "("+str(len(queryData)) + ") - Done"
	return 1

def addUserSummarys(userList, cursor):
	print "\tAdd User Summaries (" + str(len(userList)) + ")" 
	now = datetime.now()
	playerSummaries = getPlayerSummary(userList)
	print "\tLoaded Player Summaries ("+str(len(playerSummaries))+"), Start Upload to DB",
	query = "INSERT INTO `user`(`steamid`,`visibility`,`realname`,`timecreated`,`loccountrycode`,`locstatecode`,`cityid`,`lastUpdated` ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
	queryData = []
	for summary in playerSummaries:
		curSum = playerSummaries[summary]
		steamid, visibility, realname, timecreated = str(summary), str(curSum["visibility"]), str(removeNonAscii(curSum["realname"].replace("'",""))), str(curSum["timecreated"])
		loccountrycode, locstatecode, loccityid = str(curSum["loccountrycode"]), str(curSum["locstatecode"]), str(curSum["loccityid"])
		currentTime = now.strftime("%Y-%m-%d %H:%M")
		queryData.append((steamid,visibility,realname,timecreated,loccountrycode,locstatecode,loccityid,currentTime))
	try:
		cursor.executemany(query, queryData)
	except pymysql.err.IntegrityError:
		# if we override something
		pass
	print "("+str(len(queryData)) + ") - Done"
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


limit = 10000
actionCounter = 0
while actionCounter < limit:
	try:
		usersWithoutGames = getUsersWithoutGamesFromDB(500)
		actionCounter += addUserGames(usersWithoutGames, cursor)
		print("ActionCounter: " + str(actionCounter))
	except urllib2.HTTPError:
		print("HTTP Error")
		pass
    


# cursor.execute("SELECT loccountrycode, COUNT(*) FROM user group by loccountrycode")
# myDict = (cursor.fetchall())
# for i in myDict:
# 	print i
# cursor.execute("SELECT gameListLoaded, COUNT(*) FROM user group by gameListLoaded")
# myDict = (cursor.fetchall())
# for i in myDict:
# 	print i
#crawlUserIDsViaFriends(cursor, 1000)
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