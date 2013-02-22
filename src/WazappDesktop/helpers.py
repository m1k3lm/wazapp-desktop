#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import pprint
import base64

CONFIG_PATH = os.path.expanduser(os.path.join('~', '.config', 'wazapp'))
CONFIG_FILE = os.path.join(CONFIG_PATH, 'config.conf')
CONTACTS_FILE = os.path.join(CONFIG_PATH, 'contacts.conf')
LOG_FILE_TEMPLATE = os.path.join(CONFIG_PATH, 'chat_%s.log')
YOWSUP_ZIP_URL = 'https://github.com/DorianScholz/yowsup/archive/master.zip'

def checkForYowsup():
    sys.path.append(os.path.join(CONFIG_PATH, 'yowsup-master', 'src'))
    try:
        import Yowsup
    except:
        print 'Importing Yowsup failed, downloading from github:', YOWSUP_ZIP_URL
        try:
            # download and extract yowsup zip file
            import urllib2
            from tempfile import SpooledTemporaryFile
            online_file = urllib2.urlopen(YOWSUP_ZIP_URL)
            with SpooledTemporaryFile() as temp_file:
                temp_file.write(online_file.read())

                from zipfile import ZipFile
                with ZipFile(temp_file) as zip_file:
                    zip_file.extractall(CONFIG_PATH)
            online_file.close()

            # restart program to try and import again
            sys.exit(os.system(sys.argv[0]))

        except Exception as e:
            print 'Could not download or extract Yowsup:', type(e), str(e)
            print 'Please download Yowsup manually and put it in your Python path.'
            return None

    return Yowsup


def readObjectFromFile(path):
    with open(path) as fp:
        try:
            obj =  eval(fp.read())
        except Exception as e:
            print 'readObjectFromFile(): failed loading object from file "%s":\n%s' % (path, e)
            return None
        return obj

def writeObjectToFile(path, data):
    with open(path, 'w') as fp:
        pprint.pprint(data, stream=fp, indent=4)

def makeHtmlInlineImage(imageData):
    return '<img alt="Preview Image" src="data:image/png;base64,%s" />' % imageData

def makeHtmlLink(text, url):
    return '<a href="%s">%s</a>' % (url, text)

def makeHtmlImageLink(imageData, url):
    image = makeHtmlInlineImage(imageData)
    return makeHtmlLink(image, url)

def isAccountConfigured():
    if getConfig('password') is None:
        return False
    try:
        base64.b64decode(getConfig('password'))
    except TypeError as e:
        print 'isAccountConfigured(): error decoding stored password: %s' % e
        return False
    return None not in (getConfig('countryCode'), getConfig('phoneNumber'))

__config = None

def _overwriteConfig(config):
    global __config, CONFIG_PATH
    __config = config
    if not os.path.exists(CONFIG_PATH):
        os.mkdir(CONFIG_PATH)
    writeObjectToFile(CONFIG_FILE, __config)

def getConfig(key, default=None):
    global __config
    if __config is None:
        try:
            __config = readObjectFromFile(CONFIG_FILE)
        except IOError:
            __config = {}
    return __config.get(key, default)

def setConfig(key, value):
    global __config
    getConfig(key)
    __config[key] = value
    _overwriteConfig(__config)
