#!/usr/bin/python
# -*- coding: utf-8 -*-


# Copyright (C) 2009 Luis Cañas Díaz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors : Luis Cañas Díaz <lcanasdiaz@gmail.com>


from urllib import urlopen
from xml.dom.minidom import parse
from time import time
from calendar import timegm
import re
import urllib
import twitter
import ConfigParser
import os
import getopt
import sys
import urllib2
#import Exceptions

ERROR_MSG = 'Error parsing the feeds'

class FeedParser:

    def __init__(self, feed_url, feed_ns, cache_file, verbose):
        self.options = ['title', 'link']
	self.node_name = "item"
	self.feed_url = feed_url
	self.feed_ns = feed_ns
	self.cache_file = cache_file
        self.verbose = verbose
	self.xml = parse(urlopen(self.feed_url))

    def get_content(self):
        try:
            return self.get_data()
        except:
            print ERROR_MSG
            return []

    def get_data(self):
        data = []
	#xml_data = xml.getElementsByTagNameNS(self.feed_ns, self.node_name)
	xml_data = self.xml.getElementsByTagName(self.node_name)
	for node in xml_data:
	    entry={}
	    for option in self.options:
	        entry[option] = node.getElementsByTagName(option)[0].firstChild.data
	    data.append(entry)
        thenew = self.get_new_data(data)
        if ( len(thenew) < 1 ) and self.verbose:
            print "No new entries"
	return thenew

    def get_title(self):
	try:
	    xml_data = self.xml.getElementsByTagName("title")
	except:
            print ERROR_MSG
            return ""
	return xml_data[0].firstChild.data

    def add_cache(self, data):
	fd = open(self.cache_file, 'a')
	for item in data:
	    fd.write( item["link"] +"\n")
            if self.verbose:
                print item["link"] + " added to cache"
	fd.close()

    def get_new_data(self, data):
	new = []
        if self.verbose:
            print "Using cache file " + str(self.cache_file)
	try:
	    fd = open(self.cache_file, 'r')
	except IOError:
	    new = data
	    return new

	aux = fd.readlines()
	links = []
	for a in aux:
	    links.append(a.replace('\n',''))
	fd.close()
	for item in data:
	    if item["link"] not in links:
	      	new.append(item)
	    else:
	        break
	return new


class Sender:

    def __init__(self,username, password, list_messages, verbose, post, feed_title=""):
	self.username = username
	self.password = password
        self.list_messages = list_messages
        self.verbose = verbose
        self.post = post
	self.feed_title = feed_title
        self.api = twitter.Api()
	self.api = twitter.Api(username = self.username,\
				 password = self.password)
	self.list_messages.reverse()

    def send(self):
        sentm = []
	for i in self.list_messages:
	    if self.post2twitter(i):
                sentm.append(i)
        return sentm

    def compose_msg(self,link, text, feed_title=""):
	# it limits the length of the text field
	# spaces, link and feed_title are fixed
	l = len(link) + len(text) + len(feed_title) + 3
	if l > 140:
	    fixl = len(link) + len(feed_title) + 3
	    textl = 140 - fixl
	    text = text[:textl-2] + ".."

	output = text + " " + link
	if len(feed_title) > 0:
	    output = feed_title + ": "+ output
	return output	    

    def post2twitter(self, message):
	text = ""
	tinylink = self.tiny_url(message["link"])

	if len(self.feed_title) > 0:
	    text = self.compose_msg(tinylink, message["title"], self.feed_title)
	else:
	    text = self.compose_msg(tinylink, message["title"])

	if self.verbose and self.post:
	    try:
	    	uni = text.decode('unicode_escape')
	    	print "Sending: " + uni.encode('latin-1')
	    except UnicodeEncodeError:
		print "ERROR printing the message in the terminal due to encoding errors"
        try:
            if self.post:
                status = self.api.PostUpdate(text)
        except urllib2.HTTPError:
            print "Error, the message could not be posted!"
            return 0
        return 1

    def tiny_url(self, url):
	apiurl = "http://tinyurl.com/api-create.php?url="
	tinyurl = urllib.urlopen(apiurl + url).read()
	return tinyurl


FEED_NS = 'http://purl.org/rss/1.0/'

# Some stuff about the project
version = "0.1.1"
author = "(C) 2010 %s <%s>" % ("Luis Cañas Díaz", "lcanasdiaz@gmail.com")
name = "RSS to Twitter %s - http://github.com/sanacl/rsstotwitter" % (version)
credits = "\n%s \n%s\n" % (name, author)

def usage ():
    print credits
    print "Usage: rsstotwitter [configuration file] [options]"
    print """
Post feed entries in a Twitter account. It uses a cache file to avoid
sending old news.

Options:

  -h, --help         Print this usage message.
  -V, --version      Show version
  -v, --verbose      Use the verbose mode
  --cache-only       Initialize the cache with the feed entries
"""

def main():
    # Short (one letter) options. Those requiring argument followed by :
    short_opts = "hVv"
    # Long options (all started by --). Those requiring argument followed by =
    long_opts = ["help","version","cache-only","verbose"]

    #modes
    post = 1
    verbose = 0

    try:
        opts, args = getopt.getopt (sys.argv[2:], short_opts, long_opts)
        cfg_file = sys.argv[1]
    except getopt.GetoptError, e:
        print e
        sys.exit(1)
    except IndexError:
        if len(sys.argv) < 2 :
            print "\nMissing parameters!"
            usage()
            sys.exit(1)
        else:
            print "\nUnknown error"
            sys.exit(1)

    config = ConfigParser.ConfigParser()
    ioerror = 0
    try:
        config.readfp(open(cfg_file))
    except IOError:
        try:
            opts, args = getopt.getopt (sys.argv[1:], short_opts, long_opts)
        except getopt.GetoptError:
            print "\nOption not recognized"
            usage()
            sys.exit(1)
        # it isn't a file but could be an option
        ioerror = 1

    isopt = 0
    for opt, value in opts:
        if opt in ("-h", "--help", "-help"):
            usage()
            sys.exit(0)
        elif opt in ("-V", "--version"):
            print version
            sys.exit(0)
        elif opt in ("-v", "--verbose"):
            verbose = 1
            isopt = 1
        elif opt in ("--cache-only"):
            isopt = 1
            post = 0

    # it isn't a file and it isn't an option
    if ioerror and not isopt:
        print "\nIncorrect parameters"
        usage()
        sys.exit(1)

    username = config.get('Configuration', 'username', 0)
    password = config.get('Configuration', 'password', 0)
    feed_url = config.get('Configuration', 'feed_url', 0)

    try:
    	include_feed_title = config.get('Configuration', 'include_feed_title', 0)
    except ConfigParser.NoOptionError:
	include_feed_title="False"

    try:
	include_title = config.get('Configuration', 'include_title', 0)
    except ConfigParser.NoOptionError:
	include_title = None
 	pass

    fp = FeedParser(feed_url, FEED_NS, username+".cache", verbose)
    data = fp.get_content()
    if include_feed_title == 'True':
	feed_title = fp.get_title()
    	s = Sender(username, password, data, verbose, post, feed_title)
    elif include_title:
	s = Sender(username, password, data, verbose, post, include_title)
    else:
	s = Sender(username, password, data, verbose, post)
    sent_messages = s.send()
    fp.add_cache(sent_messages)

if __name__ == "__main__":
    main()
