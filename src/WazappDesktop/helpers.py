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
PICTURE_CACHE_PATH = os.path.join(CONFIG_PATH, 'pics')
if not os.path.exists(PICTURE_CACHE_PATH):
    os.mkdir(PICTURE_CACHE_PATH)

def checkForYowsup():
    return checkForModule('Yowsup', 'https://github.com/DorianScholz/yowsup/archive/master.zip', CONFIG_PATH, os.path.join('yowsup-master', 'src'))

def checkForPeewee():
    return checkForModule('peewee', 'https://github.com/coleifer/peewee/archive/2.0.7.zip', CONFIG_PATH, 'peewee-2.0.7')

def checkForModule(moduleName, downloadUrl, extractPath, importSubPath):
    import imp
    sys.path.append(os.path.join(extractPath, importSubPath))
    try:
        module = imp.load_module(moduleName, *imp.find_module(moduleName))
    except:
        print 'Importing %s failed, downloading from: %s' % (moduleName, downloadUrl)
        try:
            # download and extract zip file
            import urllib2
            from tempfile import SpooledTemporaryFile
            online_file = urllib2.urlopen(downloadUrl)
            with SpooledTemporaryFile() as temp_file:
                temp_file.write(online_file.read())

                from zipfile import ZipFile
                with ZipFile(temp_file) as zip_file:
                    zip_file.extractall(CONFIG_PATH)
            online_file.close()

            # try import again
            module = imp.load_module(moduleName, *imp.find_module(moduleName))

        except Exception as e:
            print 'Could not download or extract %s: %s %s' % (moduleName, type(e), str(e))
            print 'Please download %s manually and put it in your Python path.' % moduleName
            return None

    return module


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
