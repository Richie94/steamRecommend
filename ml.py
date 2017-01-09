try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re, sys, pickle
import config, utils
import numpy
import pymysql
from collections import defaultdict
from sklearn.model_selection import train_test_split#
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.decomposition import TruncatedSVD

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

def readInGameInformation(userList, cursor):
	userTagDict = defaultdict(lambda:[])
	userGameNameDict = defaultdict(lambda:[])
	gameTagDict = utils.getGameTagDict(cursor, "basicTags")
	gameNameDict = utils.getGameNameDict(cursor)
	userGameDict = utils.getUserGameDict(cursor)
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
	
def clfWithTpot(X, y):
	count_vect = CountVectorizer()
	X = count_vect.fit_transform(X)

	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)
	my_tpot = TPOTClassifier(generations=4)
	my_tpot.fit(X_train, y_train)
	print(my_tpot.score(X_test, y_test))
	my_tpot.export('exported_pipeline.py')

def getParams(clf):
	params = dict(
       clf__C = [0.1, 0.2, 0.3, 0.5, 1.0, 10, 50, 100, 1000, 100000],
       clf__gamma = [1E-4, 1E-3, 1E-2, 1E-1, 1.0, 10],
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

def saveObject(toSave, name):
	with open(name+'.pkl', 'wb') as output:
	    pickle.dump(toSave, output, pickle.HIGHEST_PROTOCOL)

def loadObject(name):
	with open(name, 'rb') as output:
		return pickle.load(output)

def appendArrayToX(X, newColumn):
	#probably not work as expectet so far
	X_trans = X.toarray()
	new_X = []
	for i in range(len(X_trans)):
		_tmp = [int(x) for x in X_trans[i].tolist()]
		_tmp.append(newColumn[i])
		new_X.append(_tmp)
	return new_X

def classifyAndPrintResults(clf, clfName, X, y, mode="grid"):
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)
		
	clf.fit(X_train, y_train)
	predictions = clf.predict(X_test)
	
	unique, counts = numpy.unique(predictions, return_counts=True)
	print ("Predictions",dict(zip(unique, counts)))

	unique, counts = numpy.unique(y_test, return_counts=True)
	print ("y_test",dict(zip(unique, counts)))

	if mode == "grid":
		print(clf.best_params_)

	score = accuracy_score(y_test, predictions)
	print clfName, score

def predictLand(userList,cursor, X = [], y = [], mode="grid"):
	if (X == []):	
		#somehow it seems that some user do not have steamid
		userList = [user for user in userList if "steamid" in user]
		userIdList = [user["steamid"] for user in userList if "steamid" in user]
		userTagDict,userGameDict = readInGameInformation(userIdList, cursor)

		# try to append gameamounts to X
		userGameAmount = utils.readInGameAmount(cursor)
		X_game_amounts = []

		# try to not have too much of the same continents
		continentCounter = defaultdict(lambda: 0)
		chosenContinents = defaultdict(lambda: 0)
		continentTagDict = defaultdict(lambda:defaultdict(lambda:0))

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

					# for graphs
					for tag in userTagDict[steamId]:
						continentTagDict[continent][tag] += 1

					if chosenContinents[continent] < 1000 :
						chosenContinents[continent] += 1
						
						X.append(userTagList + userGameList)
						#X_game_amounts.append(userGameAmount[steamId])
						y.append(continent)
		print continentCounter
		print chosenContinents
		print continentTagDict
		print len(X), len(y)
		saveObject(X, "x_file")
		saveObject(y, "y_file")

		counter = 0
		for c in continentTagDict.keys():
			figure(counter, figsize=(6,6))
			ax = axes([0.1, 0.1, 0.8, 0.8])
			labels = [tag for tag in continentTagDict[c]]
			fracs = [continentTagDict[c][tag] for tag in continentTagDict[c]]
			pie(fracs, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
			title(str(c))
			counter += 1
		#show()
	
	# Transform String of GameTags to Counts
	count_vect = CountVectorizer()
	X = count_vect.fit_transform(X)
	truncSVD = TruncatedSVD(n_components=100)
	X = truncSVD.fit_transform(X)

	if mode == "grid":
		clfName = "SVM"
		pipe = Pipeline([('clf', SVC())])
		clf = GridSearchCV(pipe, param_grid=getParams(clfName))
		classifyAndPrintResults(clf, clfName, X, y, mode=mode)
	else:
		classifiers = [("SVC",SVC()), ("GNB",GaussianNB()), ("RF",RandomForestClassifier()), ("AB",AdaBoostClassifier()), ("KNN",KNeighborsClassifier())]
		for clf_pair in classifiers:
			clfName = clf_pair[0]
			clf = clf_pair[1]
			classifyAndPrintResults(clf, clfName, X, y, mode=mode)

connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
cursor = connection.cursor()

X = []
y = []

try:
	X = loadObject("x_file.pkl")
	y = loadObject("y_file.pkl")
except:
	pass

userList = []
if not (len(X) > 0):
	userList = utils.readInUsers(cursor, limit=10000)

predictLand(userList, cursor, X=X, y=y, mode="other")