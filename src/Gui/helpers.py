#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import pprint

from Yowsup.Registration.v2.coderequest import WACodeRequest as WACodeRequestV2
from Yowsup.Registration.v2.regrequest import WARegRequest as WARegRequestV2

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
    return None not in (getConfig('phone'), getConfig('password'))

def configure(configFile):
    phoneNumber = raw_input('Phone number (without country code, no leading 0): ')
    countryCode = raw_input('Country code (no leading +): ')
    phone = countryCode + phoneNumber
    password = raw_input('Password (base64 encoded, leave empty to register): ')
    if not password:
        identity = raw_input('Identity (leave empty if unknown): ') or '0000000000'
        method = raw_input('Verification method (sms or voice): ') or 'sms'
        req = WACodeRequestV2(countryCode, phoneNumber, identity, method)
        res = req.send()
        print '-'*25
        print res
        print '-'*25
        code = raw_input('Received verification code: ')
        code = ''.join(code.split('-'))
        req = WARegRequestV2(countryCode, phoneNumber, code, identity)
        res = req.send()
        print '-'*25
        print res
        print '-'*25
        password = res['pw']
    _overwriteConfig({'phone': phone, 'password': password})

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
