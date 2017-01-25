try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re, sys, pickle
import config, utils
import numpy
import pymysql
from collections import defaultdict
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import MinMaxScaler

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import MaxAbsScaler
from pylab import *
import operator
from incf.countryutils import transformations
from tpot import TPOTClassifier
from scipy import sparse
from scipy.sparse import coo_matrix, vstack, lil_matrix
import sys

key = config.key

def readInGameInformation(userList, cursor):
	userTagDict = defaultdict(lambda:[])
	userGameNameDict = defaultdict(lambda:[])
	userGameTimeDict = defaultdict(lambda:{})
	gameTagDict = utils.getGameTagDict(cursor, "basicTags")
	gameNameDict = utils.getGameNameDict(cursor)
	userGameDict = utils.getUserGameDict(cursor)
	for user in userList:
		if user in userGameDict:
			try:
				gameList = userGameDict[user].split(",")
				gameTimeList = [int(game.split(":")[1]) for game in gameList]
				gameList = [int(game.split(":")[0]) for game in gameList]
				for i in range(len(gameList)):
					game = gameList[i]
					if game in gameTagDict:
						userTagDict[user].extend(gameTagDict[game])
					if game in gameNameDict:
						userGameNameDict[user].append(gameNameDict[game])
						userGameTimeDict[user][game] = gameTimeList[i]
			except Exception as e:
				print(str(e))
				pass

		#print sys.getsizeof(userGameTimeDict)
	return userTagDict,userGameNameDict, userGameTimeDict, gameNameDict
	
def clfWithTpot(X, y):
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)
	my_tpot = TPOTClassifier(generations=4)
	my_tpot.fit(X_train, y_train)
	print(my_tpot.score(X_test, y_test))
	my_tpot.export('exported_pipeline.py')

def getParams(clf):
	params = dict(
		scaler = [None, MaxAbsScaler()],
		svd = [None, TruncatedSVD(n_components=100), TruncatedSVD(n_components=250)],
       	clf__C = [0.1, 0.2, 0.3, 0.5, 1.0, 10, 50, 100, 1000, 100000],
       	clf__gamma = [1E-4, 1E-3, 1E-2, 1E-1, 1.0, 10],
   )
	paramsRF = dict(
		scaler = [None, MaxAbsScaler()],
		svd = [None, TruncatedSVD(n_components=100), TruncatedSVD(n_components=250)],
       	clf__n_estimators = [3, 10, 20, 80, 160, 320, 640],
       	clf__max_depth = [None, 50],
       	clf__class_weight = [None, "balanced"]
   )
	paramsKNN = dict(
		#scaler = [None, MaxAbsScaler()],
		#svd = [None, TruncatedSVD(n_components=100), TruncatedSVD(n_components=250)],
		#clf__n_neighbors = [2, 5, 10, 30, 50],
		#clf__weights = ["uniform", "distance"],
		#sparse input -> nur brute geht
		#clf__algorithm = ["brute"],
		#clf__leaf_size = [5, 10, 30, 30, 100, 150, 300, 600],
		#clf__metric = ["euclidean", "manhattan"],
		#clf__p = [1, 2, 3, 5, 10, 30],
		#clf__metric_params = [None],
		scaler = [MaxAbsScaler()],
		svd = [None, TruncatedSVD(n_components=100)],
		clf__n_neighbors = [50,75],
		clf__weights = ["uniform"],
		#sparse input -> nur brute geht
		clf__algorithm = ["brute"],
		clf__leaf_size = [30],
		clf__metric = ["euclidean"],
		clf__p = [30,40],
		clf__metric_params = [None],
		)
	if clf == "SVM":
		return params
	elif clf == "KNN":
		return paramsKNN
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

	if mode == "grid" or mode == "rand":
		print(clf.best_params_)

	score = accuracy_score(y_test, predictions)
	print clfName, score
	print classification_report(y_test, predictions)
	print confusion_matrix(y_test, predictions)

def memory():
    import os
    from wmi import WMI
    w = WMI('.')
    result = w.query("SELECT WorkingSet FROM Win32_PerfRawData_PerfProc_Process WHERE IDProcess=%d" % os.getpid())
    return int(result[0].WorkingSet)

def showContinentTags():
	counter = 0
	for c in continentTagDict.keys():
		figure(counter, figsize=(6,6))
		ax = axes([0.1, 0.1, 0.8, 0.8])
		labels = [tag for tag in continentTagDict[c]]
		fracs = [continentTagDict[c][tag] for tag in continentTagDict[c]]
		pie(fracs, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
		title(str(c))
		counter += 1
	show()

def predictLand(userList,cursor, X = [], y = [], mode="grid", continentLimit=1000):
	if (X == []):	
		#somehow it seems that some user do not have steamid
		userList = [user for user in userList if "steamid" in user]
		userIdList = [user["steamid"] for user in userList if "steamid" in user]
		userTagDict,userGameDict, userGameTimeDict, gameNameDict = readInGameInformation(userIdList, cursor)

		# try to append gametimes to X
		#X_game_times = []

		# try to not have too much of the same continents
		continentCounter = defaultdict(lambda: 0)
		chosenContinents = defaultdict(lambda: 0)
		continentTagDict = defaultdict(lambda:defaultdict(lambda:0))

		#X_game_times = numpy.empty([continentLimit * numberOfContinents, gameCount])
		gameCount = len(gameNameDict)
		X_game_times = lil_matrix((len(userList), gameCount))
		
		currUser = 0

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
					options = {'FX': 'Europe', 'YU': 'Europe', 'BQ':'Africa', 'SS': 'Africa', 'ZR': 'Africa', 'CW': 'South America', 'SX': 'North America'}
					continent = options[user["loccountrycode"]]
					pass
				
				if(continent != 'Europe' and continent != 'North America' and continent != 'South America'):
					continue

				continentCounter[continent] += 1

				# for graphs
				for tag in userTagDict[steamId]:
					continentTagDict[continent][tag] += 1

				if chosenContinents[continent] < continentLimit :
					chosenContinents[continent] += 1

					counter = 0;
					for game in gameNameDict:
						if game in userGameTimeDict[steamId]:
							amount = userGameTimeDict[steamId][game]
							if (amount != 0):
								X_game_times[currUser, counter] = amount
						counter += 1

					currUser += 1
					X.append(userTagList + userGameList)
					y.append(continent)

		X_reshaped = X_game_times[:currUser,:]
		
		saveObject(X, "x_file")
		saveObject(y, "y_file")
		saveObject(X_reshaped, "x_game_times_file")

		print chosenContinents
		print("cached x, y and x_game_times")

		count_vect = CountVectorizer()
		X = count_vect.fit_transform(X)
		X_combined = combineLilMats(X, X_reshaped)

		X = X_combined
	
	print ("Chosen mode: " + mode)
	if mode == "grid" or mode == "rand":
		#hier classifier changen:
		#clfName = "RF"
		#pipe = Pipeline([('scaler', MaxAbsScaler()),('svd', TruncatedSVD()),('clf', RandomForestClassifier())])
		clfName = "KNN"
		pipe = Pipeline([('scaler', MaxAbsScaler()),('svd', TruncatedSVD()),('clf', KNeighborsClassifier())])
		
		custom_verbose = 1

		if mode == "grid":	
			clf = GridSearchCV(pipe, param_grid=getParams(clfName), verbose=custom_verbose, n_jobs = 6)
		else:
			clf = RandomizedSearchCV(pipe, param_distributions=getParams(clfName), n_iter = 100, verbose=custom_verbose, n_jobs= 6)
		classifyAndPrintResults(clf, clfName, X, y, mode=mode)
	elif mode == "tpot":
		truncSVD = TruncatedSVD(n_components=150)
		X = truncSVD.fit_transform(X)
		clfWithTpot(X,y)
	else:
		classifiers = [("SVC",SVC()), ("MNB",MultinomialNB()), ("RF",RandomForestClassifier()), ("AB",AdaBoostClassifier()), ("KNN",KNeighborsClassifier())]
		for clf_pair in classifiers:
			clfName = clf_pair[0]
			clf = clf_pair[1]
		
			classifyAndPrintResults(clf, clfName, X, y, mode=mode)

def combineLilMats(lilMat1, lilMat2):
	combined = lil_matrix((lilMat1.shape[0], lilMat1.shape[1]+lilMat2.shape[1]))
	combined[:, :lilMat1.shape[1]] = lilMat1
	combined[:, lilMat1.shape[1]:lilMat1.shape[1]+lilMat2.shape[1]] =lilMat2
	return combined

if __name__ == '__main__':
	connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
	cursor = connection.cursor()

	X = []
	y = []
	# try to append gametimes to X
	X_game_times = lil_matrix((1,1))
	X_comb = lil_matrix((1,1))

	try:
		X = loadObject("x_file.pkl")
		y = loadObject("y_file.pkl")
		count_vect = CountVectorizer()
		X = count_vect.fit_transform(X)
		X_game_times = loadObject("x_game_times_file.pkl")
		X_comb = combineLilMats(X, X_game_times)

		print("X: " + str(X.shape))
		print("X_game_times: " + str(X_game_times.shape))
		print("Combined: " + str(X_comb.shape))

		print("loaded x (%s), y (%s) and x_game_times (%s) from file" % (X.shape[0], len(y), X_game_times.shape[0]))
		
	except Exception as e:
		print str(e)
		pass




	userList = []
	#userAmount = 10000
	userAmount = 100000
	#continentLimit = userAmount/6
	continentLimit = userAmount/3
	if not (X_game_times.shape[0] > continentLimit * 2.5 ):
		print "Load New Users"
		userList = utils.readInUsers(cursor, limit=userAmount)
		X_game_times, X, y, X_comb = [], [], [], []

	predictLand(userList, cursor, continentLimit=continentLimit, X=X_comb, y=y, mode="grid")