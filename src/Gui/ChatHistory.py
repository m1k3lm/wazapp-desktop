#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from helpers import LOG_FILE_TEMPLATE

class ChatHistory(object):
    def __init__(self):
        super(ChatHistory, self).__init__()
        self._conversations = {}

    def get(self, conversationId):
        if conversationId not in self._conversations:
            messageList = []
            try:
                with codecs.open(LOG_FILE_TEMPLATE % conversationId, 'r', 'utf8') as logfile:
                    for line in logfile:
                        timestamp, sender, receiver, message = line.rstrip('\n').split(';', 3)
                        timestamp = float(timestamp)
                        messageList.append((timestamp, sender, receiver, message))
            except IOError:
                pass
            self._conversations[conversationId] = messageList
        return self._conversations[conversationId]

    def log(self, conversationId, timestamp, sender, receiver, message):
        self.get(conversationId).append((timestamp, sender, receiver, message))
        logfile = codecs.open(LOG_FILE_TEMPLATE % conversationId, 'a', 'utf8')
        logfile.write('%s;%s;%s;%s\n' % (timestamp, sender, receiver, message))
        logfile.close()
