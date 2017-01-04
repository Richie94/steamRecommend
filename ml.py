try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re, sys
import config
import numpy
import pymysql
from collections import defaultdict
from sklearn.model_selection import train_test_split#
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier

from sklearn.metrics import accuracy_score
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import MinMaxScaler
from pylab import *
import operator
from incf.countryutils import transformations
from tpot import TPOTClassifier

key = config.key

def readInUsers(cursor, limit=2000):
	userList = []
	query = """Select * from user where loccountrycode !='' LIMIT %s;""" % limit
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
	query = "SET group_concat_max_len = 32384"
	cursor.execute(query)
	query = "SELECT steamid, GROUP_CONCAT(gameid SEPARATOR ', ') as gameList FROM user_games WHERE timeforever > 120 GROUP BY steamid"
	cursor.execute(query)
	user_games = cursor.fetchall()
	for user_game in user_games:
		userGameDict[user_game["steamid"]] = user_game["gameList"]
	return userGameDict

def getGameTagDict(cursor):
	gameTagDict = {}
	query = "Select id,basicTags from game;"
	cursor.execute(query)
	gameTags = cursor.fetchall()
	for tag in gameTags:
		gameTagDict[tag["id"]] = tag["basicTags"].split(",")
	return gameTagDict

def getGameNameDict(cursor):
	gameTagDict = {}
	query = "Select id,name from game;"
	cursor.execute(query)
	gameTags = cursor.fetchall()
	for tag in gameTags:
		gameTagDict[tag["id"]] = tag["name"]
	return gameTagDict


def readInGameInformation(userList, cursor):
	userTagDict = defaultdict(lambda:[])
	userGameNameDict = defaultdict(lambda:[])
	gameTagDict = getGameTagDict(cursor)
	gameNameDict = getGameNameDict(cursor)
	userGameDict = getUserGameDict(cursor)
	for user in userList:
		if user in userGameDict:
			gameList = userGameDict[user].split(",")
			gameList = [int(game) for game in gameList]
			for game in gameList:
				if game in gameTagDict:
					userTagDict[user].extend(gameTagDict[game])
				if game in gameNameDict:
					userGameNameDict[user].append(gameNameDict[game])
	return userTagDict,userGameNameDict
	
def clfWithTpot(X_g,y_g):
	count_vect = CountVectorizer()
	X = count_vect.fit_transform(X_g)

	X_train, X_test, y_train, y_test = train_test_split(X, y_g, test_size=.1)
	my_tpot = TPOTClassifier(generations=4)
	my_tpot.fit(X_train, y_train)
	print(my_tpot.score(X_test, y_test))
	my_tpot.export('exported_pipeline.py')

def getParams(clf):
	params = dict(
       clf__C = [0.1, 0.2, 0.3, 0.5, 1.0, 10, 100],
       clf__gamma = [1E-3, 1E-2, 1E-1, 1.0],
   )
	paramsRF = dict(
       clf__n_estimators = [3,5,10,15,20],
       clf__max_features = ["auto","log2"],
       clf__max_depth = [None, 10, 20, 30, 50],
       clf__class_weight = [None, "balanced"]
   )
	if clf == "SVM":
		return params
	elif clf == "RF":
		return paramsRF

# TODO:	
# Nur gametags von spielen mit mehr als 0 gespielt
#
#
def predictLand(userList,cursor):
	userList = [user for user in userList if "steamid" in user]
	userIdList = [user["steamid"] for user in userList if "steamid" in user]
	userTagDict,userGameDict = readInGameInformation(userIdList, cursor)

	print "Len of dicts ", len(userTagDict), len(userGameDict)

	userGameAmount = readInGameAmount(cursor)
	X = []
	y = []
	X_game_amounts = []
	# try to not have too much of the same continents
	continentCounter = defaultdict(lambda: 0)
	chosenContinents = defaultdict(lambda: 0)

	for user in userList:
		steamId = str(user["steamid"])
		if str(steamId) in userTagDict:
			userTagList = ' '.join(userTagDict[steamId])
			userGameList = ' '.join(userGameDict[steamId])
			continent = ""
			# threshold fuer anzahl userTags?
			try:
				# Maybe invalid countrycode given
				continent = transformations.cca_to_ctn(user["loccountrycode"])
			except Exception as e:
				pass
			if continent != "":
				continentCounter[continent] += 1

				if chosenContinents[continent] < 1000 :
					chosenContinents[continent] += 1
					
					X.append(userTagList + userGameList)
					#X_game_amounts.append(userGameAmount[steamId])
					y.append(continent)
	print continentCounter
	print chosenContinents
	print len(X), len(y)
	
	#pipe = Pipeline([('clf', RandomForestClassifier())])
	#clf = GridSearchCV(pipe, param_grid=getParams("RF"))
	
	classifiers = [("SVC",SVC()), ("MNB",MultinomialNB()), ("RF",RandomForestClassifier()), ("AB",AdaBoostClassifier()), ("KNN",KNeighborsClassifier())]
	
	# Transform String of GameTags to Counts
	count_vect = CountVectorizer()
	X = count_vect.fit_transform(X)

	# Append Amount of Games
	#X_trans = X.toarray()
	#X = []
	#for i in range(len(X_trans)):
	#	_tmp = [int(x) for x in X_trans[i].tolist()]
	#	_tmp.append(X_game_amounts[i])
	#	X.append(_tmp)

	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)
	for i in range(len(classifiers)):
		clf = classifiers[i][1]
		clf.fit(X_train, y_train)
		predictions = clf.predict(X_test)
		
		unique, counts = numpy.unique(predictions, return_counts=True)
 		print ("Predictions",dict(zip(unique, counts)))

 		unique, counts = numpy.unique(y_test, return_counts=True)
 		print ("y_test",dict(zip(unique, counts)))
		
		#print(clf.best_params_)

		score = accuracy_score(y_test, predictions)
		print classifiers[i][0], score

connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()
userList = readInUsers(cursor, limit=10000)
predictLand(userList, cursor)