/*
Navicat MySQL Data Transfer

Source Server         : localhost
Source Server Version : 50704
Source Host           : localhost:3306
Source Database       : pytest

Target Server Type    : MYSQL
Target Server Version : 50704
File Encoding         : 65001

Date: 2016-11-02 11:59:19
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for `game`
-- ----------------------------
DROP TABLE IF EXISTS `game`;
CREATE TABLE `game` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;


-- ----------------------------
-- Table structure for `user`
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `steamid` varchar(17) NOT NULL,
  `visibility` tinyint(1) unsigned NOT NULL,
  `realname` varchar(75) DEFAULT NULL,
  `timecreated` int(11) NOT NULL,
  `cityid` int(10) unsigned DEFAULT NULL,
  `loccountrycode` varchar(2) DEFAULT NULL,
  `locstatecode` varchar(12) DEFAULT NULL,
  `loccityid` int(11) DEFAULT NULL,
  `lastUpdated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`steamid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- ----------------------------
-- Table structure for `user_achievements`
-- ----------------------------
DROP TABLE IF EXISTS `user_achievements`;
CREATE TABLE `user_achievements` (
  `steamid` varchar(17) NOT NULL,
  `appid` int(10) unsigned NOT NULL,
  `achievement` varchar(255) NOT NULL,
  `achieved` tinyint(1) NOT NULL,
  PRIMARY KEY (`steamid`,`appid`),
  CONSTRAINT `user_achievements_ibfk_1` FOREIGN KEY (`steamid`) REFERENCES `user` (`steamid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;



-- ----------------------------
-- Table structure for `user_friends`
-- ----------------------------
DROP TABLE IF EXISTS `user_friends`;
CREATE TABLE `user_friends` (
  `steamid` varchar(17) NOT NULL,
  `friendsteamid` varchar(17) NOT NULL,
  `relationship` varchar(255) NOT NULL,
  `friendsSince` int(10) NOT NULL,
  PRIMARY KEY (`steamid`,`friendsteamid`),
  CONSTRAINT `steamidfriend` FOREIGN KEY (`steamid`) REFERENCES `user` (`steamid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;



-- ----------------------------
-- Table structure for `user_games`
-- ----------------------------
DROP TABLE IF EXISTS `user_games`;
CREATE TABLE `user_games` (
  `steamid` varchar(17) NOT NULL,
  `gameid` varchar(255) NOT NULL,
  `timetwoweeks` int(11) NOT NULL,
  `timeforever` int(11) NOT NULL,
  PRIMARY KEY (`steamid`,`gameid`),
  CONSTRAINT `steamidusergames` FOREIGN KEY (`steamid`) REFERENCES `user` (`steamid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- INSERT INTO `user_friends` (`steamid`,`friendsteamid`,`relationship`,`friendsSince`) VALUES ('a', 'b', '1', '2');
-- INSERT INTO `user`(`steamid`,`visibility`,`realname`,`timecreated`,`cityid`,`loccountrycode`,`locstatecode`,`loccityid`) VALUES ('a', '1', 'a', '123', '1', '2', '3', '4');
-- INSERT INTO `user_games`(`steamid`,`gameid`, `timetwoweeks`,`timeforever`) VALUES ('a', 'a', '1', '2');
-- INSERT INTO `user_achievements` (`steamid`,`appid`,`achievement`,`achieved`) VALUES ('a', '1', 'c', '1');
-- INSERT INTO `game`(`id`,`name`) VALUES ('1', '2');

