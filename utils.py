from collections import defaultdict
from incf.countryutils import transformations
import pymysql
import config
from operator import itemgetter

def normalizeTagAn():

	continentTags = defaultdict(lambda:defaultdict(lambda:0))
	with open("tag_ana_country.txt", "r") as f:
		text = f.read().split("\n")
		for line in text:
			parts = line.split("\t")
			if len(parts) == 3 and parts[1] != "":
				try:
					continent = transformations.cca_to_ctn(parts[0])
					continentTags[continent][parts[1]] += int(parts[2])
				except:
					pass

		# count total
		totalTagOccurences = defaultdict(lambda: 0)
		for continent in continentTags:
			for tag in continentTags[continent]:
				totalTagOccurences[continent] += continentTags[continent][tag]

		#normalize
		normalizedContinentTags = defaultdict(lambda:defaultdict(lambda:0))
		for continent in continentTags:
			for tag in continentTags[continent]:
				normalizedContinentTags[continent][tag] = float(continentTags[continent][tag])/float(totalTagOccurences[continent])


		#write it to file
		with open("continentTags.txt", 'w') as g:
			for continent in continentTags:
				for tag in normalizedContinentTags[continent]:
					g.write(str(continent) + "\t" + str(tag) + "\t" + str(normalizedContinentTags[continent][tag]) + "\n")

def getGameTagDict(cursor, tagName="transformedGameTags"):
	gameTagDict = {}
	query = "Select id,"+ str(tagName) +" from game;"
	cursor.execute(query)
	gameTags = cursor.fetchall()
	for tag in gameTags:
		gameTagDict[tag["id"]] = tag[tagName].split(",")
	print("GameTagDict loaded")
	return gameTagDict

def getGameNameDict(cursor):
	gameTagDict = {}
	query = "Select id,name from game;"
	cursor.execute(query)
	gameTags = cursor.fetchall()
	for tag in gameTags:
		gameTagDict[tag["id"]] = tag["name"]
	return gameTagDict

def readInGameAmount(cursor):
	amountDict = {}
	query = "Select steamid, COUNT(gameid) as amount from user_games Group By steamid"
	cursor.execute(query)
	userList = cursor.fetchall()
	for user in userList:
		amountDict[user["steamid"]] = user["amount"]
	return amountDict

def readInUsers(cursor, limit=2000):
	userList = []
	query = """Select * from user where loccountrycode !='' LIMIT %s;""" % limit
	cursor.execute(query)
	userList = cursor.fetchall()
	for user in userList:
		userDict = {}
		if "steamid" in user:
			userDict["steamId"] = str(user["steamid"])
			userDict["visibility"] = user["visibility"]
			userDict["realName"] = user["realname"]
			userDict["timecreated"] = user["timecreated"]
			userDict["cityid"] = user["cityid"]
			userDict["loccountrycode"] = user["loccountrycode"]
			userDict["locstatecode"] = user["locstatecode"]
			userList.append(userDict)
	print("Users Loaded")
	return userList

def getUserGameDict(cursor):
	userGameDict = {}
	#results can be larger then default
	query = "SET group_concat_max_len = 32384"
	cursor.execute(query)
	query = "SELECT steamid, GROUP_CONCAT(gameid SEPARATOR ', ') as gameList FROM user_games WHERE timeforever > 120 GROUP BY steamid"
	cursor.execute(query)
	user_games = cursor.fetchall()
	for user_game in user_games:
		userGameDict[str(user_game["steamid"])] = user_game["gameList"]
	print("UserGameDict loaded")
	return userGameDict

def getSubstitutionDict():
	substitutionDict = {}
	with open("maxCoOcc.txt", "r") as f:
		lines = f.read().split("\n")
		for line in lines:
			foo = line.split("\t")
			if len(foo) == 3:
				w1, w2, amount = foo[0], foo[1], int(foo[2]) 
				# if amount is really great its a strong word
				if amount < 3000:
					substitutionDict[w2] = w1
	return substitutionDict

def transformTags():
	connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
	connection.autocommit(True)
	cursor = connection.cursor()
	gameTagDict = getGameTagDict(cursor)
	substitutionDict = getSubstitutionDict()
	cb = 0
	ca = 0
	with open("newGames.txt", "w") as f:
		for game in gameTagDict:
			newTags = set()
			cb += len(gameTagDict[game])
			for tag in gameTagDict[game]:
				newTag = tag
				while newTag in substitutionDict:
					newTag = substitutionDict[newTag]
				newTags.add(newTag)

			ca += len(newTags)
			f.write(str(game) + "\t" + ','.join(newTags) + "\n")
			#print "UPDATE game SET transformedGameTags = " + ','.join(newTags) + "WHERE id = " + str(game)
			cursor.execute("UPDATE game SET basicTags = '" + ','.join(newTags) + "' WHERE id = " + str(game))
	print "Before: ", cb
	print "After: ", ca




def findCoOcc():
	connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
	connection.autocommit(True)
	cursor = connection.cursor()
	gameTagDict = getGameTagDict(cursor)
	togetherDict = defaultdict(lambda: 0)
	tagAmountDict = defaultdict(lambda: 0)

	counter = -1
	for entry in gameTagDict:
		counter += 1
		print counter
		for tag1 in gameTagDict[entry]:
			tagAmountDict[tag1] += 1
			for tag2 in gameTagDict[entry]:
				if tag1 != tag2:
					togetherDict[(tag1, tag2)] += 1

	for entry in togetherDict:
		reverse = (entry[1], entry[0])
		if reverse in togetherDict:
			togetherDict[entry] += togetherDict[reverse]
			togetherDict[reverse] = 0

	with open("findCoOcc.txt", "w") as f:
		for entry in togetherDict:
			if togetherDict[entry] > 0:
				f.write(str(entry) + "\t" + str(togetherDict[entry]) + "\n")

	togetherListDict = defaultdict(lambda: [])
	for entry in togetherDict:
		togetherListDict[entry[0]].append((entry[1], togetherDict[entry]))
		togetherListDict[entry[1]].append((entry[0], togetherDict[entry]))


	with open("maxCoOcc.txt", "w") as f:
		for entry in togetherListDict:
			# get tag which ocurred most together
			maxTuple = max(togetherListDict[entry] ,key=itemgetter(1))
			# see which tag is more often used
			if tagAmountDict[entry] > tagAmountDict[maxTuple[0]]:
				f.write(entry + "\t" + str(maxTuple[0]) + "\t" + str(maxTuple[1]) + "\n")
			else:
				f.write(maxTuple[0] + "\t" + str(entry) + "\t" + str(maxTuple[1]) + "\n")


def thresh(x):
	if len(x) < 3:
		return 0
	if len(x) < 5:
		return 2
	if len(x) < 10:
		return 3
	return 4

def findNeighbourTags():
	connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
	connection.autocommit(True)
	cursor = connection.cursor()
	gameTagDict = getGameTagDict(cursor)
	newGameTagDict = {}
	staying = list()
	counter = -1
	for entry in gameTagDict:
		counter += 1
		entrySet = set(gameTagDict[entry])
		print counter
		
		if counter == 0:
			newGameTagDict[entry] = entrySet
			staying.append(entrySet)

		
		t = thresh(entrySet)
		found = 0;
		for stood in staying:
			if len(stood.symmetric_difference(entrySet)) < t:
				newGameTagDict[entry] = stood
				found = 1
				break

		if found == 0:
			newGameTagDict[entry] = entrySet
			staying.append(entrySet)
			

	print "Length:" + str(len(staying))
	
	with open("new_gametags.txt", "w") as f:
		for entry in newGameTagDict:
			f.write(str(entry) + "\t" + ','.join(newGameTagDict[entry]) + "\n")

def getClassAmount():
	amountDict = defaultdict(lambda: 0)
	with open("newGames.txt", "r") as f:
		lines = f.read().split("\n")
		for line in lines:
			foo = line.split("\t")
			if len(foo) == 2:
				amountDict[foo[1]] += 1
	print len(amountDict)


#transformTags()

