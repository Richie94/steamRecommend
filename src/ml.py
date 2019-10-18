try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import json, re, sys, pickle
from src import config, utils
import numpy
import pymysql
from collections import defaultdict
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.decomposition import TruncatedSVD, SparsePCA
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans

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
	gameTagDict = utils.getGameTagDict(cursor, "transformedGameTags")
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
				print("ReadInGameInformation: ", str(e))
				pass

	return userTagDict,userGameNameDict, userGameTimeDict, gameNameDict
	
def clfWithTpot(X, y):
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)
	my_tpot = TPOTClassifier(generations = 10, verbosity = 2)
	my_tpot.fit(np.array(X_train), np.array(y_train))
	print(my_tpot.score(np.array(X_test), np.array(y_test)))
	my_tpot.export('exported_pipeline.py')
	predictions = my_tpot.predict(np.array(X_test))
	print(confusion_matrix(y_test, predictions))


def getParams(clf):
	params = dict(
		scaler = [None, MaxAbsScaler()],
		svd = [None, TruncatedSVD(n_components=100), TruncatedSVD(n_components=250)],
       	clf__C = [0.1, 0.2, 0.3, 0.5, 1.0, 10, 50, 100, 1000, 100000],
       	clf__gamma = [1E-4, 1E-3, 1E-2, 1E-1, 1.0, 10],
   )
	paramsRF = dict(
		clf__n_estimators = [320],
       	clf__max_depth = [None],
       	clf__min_samples_split = [2], 
       	clf__class_weight = [None]
   )
	paramsAB = dict(
		clf__n_estimators = [50, 100, 150],
		scaler = [None, MaxAbsScaler()]
		)
	paramsKNN = dict(
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
	elif clf == "RF":
		return paramsRF
	elif clf == "AB":
		return paramsAB

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

def arrayDiff(a1, a2):
	diff = 0
	maxDiff = 0
	for i in range(len(a1)):
		_diff = abs(a1[i]-a2[i])
		diff += _diff
		if _diff > maxDiff:
			maxDiff = _diff
	return diff, maxDiff


def classifyAndPrintResults(clf, clfName, X, y, mode="grid", X_my = []):
	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1)
		
	clf.fit(X_train, y_train)
	predictions = clf.predict(X_test)
	
	unique, counts = numpy.unique(predictions, return_counts=True)
	print ("Predictions",dict(zip(unique, counts)))

	unique, counts = numpy.unique(y_test, return_counts=True)
	print ("y_test",dict(zip(unique, counts)))

	if X_my != []:
		print(X_my)
		print(clf.predict(X_my))

	if mode == "grid" or mode == "rand":
		print(clf.best_params_)

	score = accuracy_score(y_test, predictions)
	print(clfName, score)
	print(classification_report(y_test, predictions))
	print(confusion_matrix(y_test, predictions))

def memory():
	import os
	from wmi import WMI
	w = WMI('.')
	result = w.query("SELECT WorkingSet FROM Win32_PerfRawData_PerfProc_Process WHERE IDProcess=%d" % os.getpid())
	return int(result[0].WorkingSet)

def showContinentTags(continentTagDict):
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
		userIdList = [user["steamId"] for user in userList]
		userTagDict,userGameDict, userGameTimeDict, gameNameDict = readInGameInformation(userIdList, cursor)

		print("All Game Information from DB collected")

		# try to not have too much of the same continents
		continentCounter = defaultdict(lambda: 0)
		chosenContinents = defaultdict(lambda: 0)
		continentTagDict = defaultdict(lambda:defaultdict(lambda:0))

		gameCount = len(gameNameDict)
		X_game_times = lil_matrix((len(userList), gameCount))

		currUser = 0

		for user in userList:
			if currUser % 300 == 0:
				print(currUser, chosenContinents)
			steamId = str(user["steamId"])

			if str(steamId) in userTagDict:
				userTagList = ' '.join(userTagDict[steamId])
				userGameList = ' '.join(userGameDict[steamId])

				continent = ""
				try:
					# Maybe invalid countrycode given
					continent = transformations.cca_to_ctn(user["loccountrycode"])
				except Exception as e:
					options = {'FX': 'Europe', 'YU': 'Europe', 'BQ':'Africa', 'SS': 'Africa', 'ZR': 'Africa', 'CW': 'South America', 'SX': 'North America'}
					continent = options[user["loccountrycode"]]
					pass

				if continent == 'Antarctica' or continent == 'Africa' or continent == 'Oceania':
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

		X_reshaped = lil_matrix(X_game_times[:currUser,:])
		
		saveObject(X, "x_file")
		saveObject(y, "y_file")
		saveObject(X_reshaped, "x_game_times_file")

		print(chosenContinents)
		print("cached x, y and x_game_times")

		count_vect = CountVectorizer()

		X = count_vect.fit_transform(X)
		X_combined = combineLilMats(X, X_reshaped)

		saveObject(X_combined, "X_comb")

		#X_my = count_vect.fit_transform(X_my)
		#X_my2 = combineLilMats(X_my, X_game_times2)

		X = X_combined
	
	print("Chosen mode: " + mode)
	print("X Data in Shape: " + str(X.shape))
	svd = TruncatedSVD(n_components=3)
	X = svd.fit_transform(X)

	#from mpl_toolkits.mplot3d import Axes3D
	#import matplotlib.pyplot as plt
	#fig = plt.figure()
	#ax = plt.axes(projection='3d')
	#contToNb = {'Europe': 1, 'North America': 2, 'Asia': 3, 'South America': 4}
	#c = [contToNb[x] for x in y ]
	#x_ = [i[0] for i in X]
	#y_ = [i[1] for i in X]
	#z_ = [i[2] for i in X]
	#ax.scatter(x_, y_, z_, c=c)
	#plt.show()

	print ("X Data in Shape after TruncatedSVD: " + str(X.shape))
	if mode == "grid" or mode == "rand":
		
		clfName = "AB"
		pipe = Pipeline([('scaler', MaxAbsScaler()),('clf', AdaBoostClassifier())])
		if mode == "grid":	
			clf = GridSearchCV(pipe, param_grid=getParams(clfName), verbose = 10, n_jobs = 2)
		else:
			clf = RandomizedSearchCV(pipe, param_distributions=getParams(clfName), n_iter = 20, verbose = 10, n_jobs = 2)
		classifyAndPrintResults(clf, clfName, X, y, mode=mode)
	elif mode == "tpot":
		clfWithTpot(X,y)
	else:
		classifiers = [("SVC",SVC()), ("RF",RandomForestClassifier()), ("AB",AdaBoostClassifier()), ("KNN",KNeighborsClassifier())]
		for clf_pair in classifiers:
			clfName = clf_pair[0]
			clf = clf_pair[1]
		
			classifyAndPrintResults(clf, clfName, X, y, mode=mode)

def combineLilMats(lilMat1, lilMat2):
	combined = lil_matrix((lilMat1.shape[0], lilMat1.shape[1]+lilMat2.shape[1]))
	partSize = 1000
	for i in range(lilMat1.shape[1]/partSize):
		combined[:, i*partSize:(i+1)*partSize] = lilMat1[:, i*partSize:(i+1)*partSize]

	for i in range(lilMat2.shape[1]/partSize):
		combined[:, lilMat1.shape[1]+i*partSize:lilMat1.shape[1]+(i+1)*partSize] = lilMat2[:, i*partSize:(i+1)*partSize]
	return combined


if __name__ == "__main__":
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

		print("X: " + str(X.shape))

		
	except Exception as e:
		print(str(e))
		pass

	userList = []
	userAmount = 100000
	continentLimit = 5000

	predictLand(userList, cursor, continentLimit=continentLimit, X=X, y=y, mode="grid")