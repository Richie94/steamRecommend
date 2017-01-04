from pylab import *
from collections import defaultdict
import operator
import pymysql
import utils, config

def read_continent_tags():
	#load countryTags
	continentTags = defaultdict(lambda:[])
	with open("continentTags.txt", "r") as f:
		text = f.read().split("\n")
		for line in text:
			parts = line.split("\t")
			if len(parts) == 3 and parts[1] != "":
				continentTags[parts[0]].append((parts[1],float(parts[2])))
	return continentTags

def getBasicContinentTagsFromDB():
	continentTags = defaultdict(lambda:[])
	connection = pymysql.connect(host=config.db_ip, port=int(config.db_port), user=config.db_user, passwd=config.db_pass, db="steamrec", autocommit = True, cursorclass=pymysql.cursors.DictCursor)
	cursor = connection.cursor()
	basicTagDict = utils.getGameTagDict(cursor, "basicTags")
	userGameDict = utils.getUserGameDict(cursor)
	userList = utils.readInUsers(cursor, limit=10000)

	for user in userList:
		# 1. get gamelist for every user
		userGameList = userGameDict[user]
		# 2. check for every user his continent/country



	

getBasicContinentTagsFromDB()

continentTags = read_continent_tags()

#get Top10 for each
continentTagsTop10 = {}
for continent in continentTags:
	sortedTags = sorted(continentTags[continent], key=lambda x: x[1], reverse=True)
	continentTagsTop10[continent] = sortedTags[:10]


# calculate average intersection
pairCounter, intersectionSum = 0, 0
for continentA in continentTagsTop10:
	for continentB in continentTagsTop10:
		if continentA != continentB and continentA>continentB:
			pairCounter += 1
			continentIntersect = len(set([tag[0] for tag in continentTagsTop10[continentA]]).intersection([tag[0] for tag in continentTagsTop10[continentB]]))
			intersectionSum += continentIntersect
print("Average Intersecting tags in Top10", intersectionSum/pairCounter)

counter = 0
for c in continentTagsTop10.keys():
	figure(counter, figsize=(6,6))
	ax = axes([0.1, 0.1, 0.8, 0.8])
	labels = [tag[0] for tag in continentTagsTop10[c]]
	fracs = [tag[1]*100 for tag in continentTagsTop10[c]]
	pie(fracs, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
	title(str(c))
	counter += 1
#show()






