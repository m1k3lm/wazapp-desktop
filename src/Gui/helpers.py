#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import pprint
import base64

CONFIG_PATH = os.path.expanduser('~/.whatsapp')
CONFIG_FILE = CONFIG_PATH + '/config.conf'
CONTACTS_FILE = CONFIG_PATH + '/contacts.conf'
LOG_FILE_TEMPLATE = CONFIG_PATH + '/chat_%s.log'

def readObjectFromFile(path):
    with open(path) as fp:
        return eval(fp.read())

def writeObjectToFile(path, data):
    with open(path, 'w') as fp:
        pprint.pprint(data, stream=fp, indent=4, width=160)

def makeHtmlInlineImage(imageData):
    return '<img alt="Preview Image" src="data:image/png;base64,%s" />' % imageData

def makeHtmlLink(text, url):
    return '<a href="%s">%s</a>' % (url, text)

def makeHtmlImageLink(imageData, url):
    image = makeHtmlInlineImage(imageData)
    return makeHtmlLink(image, url)

def isConfigured():
    if getConfig('password') is None:
        return False
    try:
        base64.b64decode(getConfig('password'))
    except TypeError as e:
        print 'isConfigured(): error decoding stored password: %s' % e
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
