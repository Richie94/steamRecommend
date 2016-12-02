try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re, sys
import config
import pymysql
from collections import defaultdict
from sklearn.model_selection import train_test_split#
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import MinMaxScaler

key = config.key

def readInUsers(cursor, limit=2000):
	userList = []
	query = """Select * from user where loccountrycode !='' and realname != "" LIMIT %s;""" % limit
	cursor.execute(query)
	userList = cursor.fetchall()
	for user in userList:
		userDict = {}
		if "steamid" in user:
			userDict["steamId"] = user["steamid"]
			userDict["visibility"] = user["visibility"]
			userDict["realName"] = user["realname"]
			userDict["timecreated"] = user["timecreated"]
			userDict["cityid"] = user["cityid"]
			userDict["loccountrycode"] = user["loccountrycode"]
			userDict["locstatecode"] = user["locstatecode"]
			userList.append(userDict)
	print("Users Loaded")
	return userList

def readInGameAmount(cursor):
	amountDict = {}
	query = "Select steamid, COUNT(gameid) as amount from user_games Group By steamid"
	cursor.execute(query)
	userList = cursor.fetchall()
	for user in userList:
		amountDict[user["steamid"]] = user["amount"]
	return amountDict

def getUserGameDict(cursor):
	userGameDict = {}
	#results can be larger then default
	query = "SET group_concat_max_len = 16384"
	cursor.execute(query)
	query = "SELECT steamid, GROUP_CONCAT(gameid SEPARATOR ', ') as gameList FROM user_games GROUP BY steamid"
	cursor.execute(query)
	user_games = cursor.fetchall()
	for user_game in user_games:
		userGameDict[user_game["steamid"]] = user_game["gameList"]
	return userGameDict

def getGameTagDict(cursor):
	gameTagDict = {}
	query = "Select id,gameTags from game;"
	cursor.execute(query)
	gameTags = cursor.fetchall()
	for tag in gameTags:
		gameTagDict[tag["id"]] = tag["gameTags"]
	return gameTagDict


def readInGameTags(userList, cursor):
	userTagDict = defaultdict(lambda:[])
	gameTagDict = getGameTagDict(cursor)
	userGameDict = getUserGameDict(cursor)
	for user in userList:
		if user in userGameDict:
			gameList = userGameDict[user].split(",")
			gameList = [int(game) for game in gameList if game.isdigit()]
			for game in gameList:
				if game in gameTagDict:
					userTagDict[user].append(gameTagDict[game])
	return userTagDict
	
# Nur gametags von spielen mit mehr als 0 gespielt
#
#
def predictLand(userList,cursor):
	userList = [user for user in userList if "steamid" in user]
	userIdList = [user["steamid"] for user in userList if "steamid" in user]
	userTagDict = readInGameTags(userIdList, cursor)
	X = []
	y = []
	for user in userList:
		steamId = user["steamid"]
		if str(steamId) in userTagDict:
			userTags = userTagDict[steamId]
			X.append(''.join(userTags))
			y.append(user["loccountrycode"])
	print len(X),len(y)
	
	params = dict(
       clf__C = [0.1, 0.2, 0.3, 0.5, 1.0, 10, 100],
       clf__gamma = [1E-3, 1E-2, 1E-1, 1.0],
   )

	#pipe = Pipeline([('clf', SVC())])
	#clf = GridSearchCV(pipe, param_grid=params, cv=10)

	for i in range(1):
		count_vect = CountVectorizer()
		X = count_vect.fit_transform(X)

		X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)

		
		#tfidf_transformer = TfidfTransformer()
		#X_train_tfidf = tfidf_transformer.fit_transform(X_train)

		clf = SVC()
		clf.fit(X_train, y_train)
		predictions = clf.predict(X_test)
		#for i in range(len(X_test)):
		#	print X_test[i], y_test[i], predictions[i]

		score = accuracy_score(y_test, predictions)
		print score






connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()
userList = readInUsers(cursor)
predictLand(userList, cursor)