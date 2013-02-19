#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
from helpers import LOG_FILE_TEMPLATE

class ChatHistory(object):
    def __init__(self):
        super(ChatHistory, self).__init__()
        self._conversations = {}

    def _parseLog(self, conversationId):
        history = {'list': [], 'dict': {}}
        try:
            with codecs.open(LOG_FILE_TEMPLATE % conversationId, 'r', 'utf8') as logfile:
                for line in logfile:
                    messageId, timestamp, sender, receiver, message = line.rstrip('\n').split(';', 4)
                    timestamp = float(timestamp)
                    data = (messageId, timestamp, sender, receiver, message)
                    history['list'].append(data)
                    history['dict'][messageId] = data
        except IOError:
            pass
        return history

    def get(self, conversationId):
        if conversationId not in self._conversations:
            self._conversations[conversationId] = self._parseLog(conversationId)
        return self._conversations[conversationId]

    def add(self, conversationId, messageId, timestamp, sender, receiver, message):
        history = self.get(conversationId)
        # if message is already in the logs and it is from my self, mark it as the answer message
        if messageId in history['dict'] and sender == receiver:
            messageId += '*'
        data = (messageId, timestamp, sender, receiver, message)
        # if message is already in the logs, don't show it again
        if messageId in history['dict']:
            print 'ChatHistory.add(): received duplicate message:', data
            return None
        message = u'<br>'.join(message.split('\n'))
        history['list'].append(data)
        history['dict'][messageId] = data
        logfile = codecs.open(LOG_FILE_TEMPLATE % conversationId, 'a', 'utf8')
        logfile.write('%s;%s;%s;%s;%s\n' % (messageId, timestamp, sender, receiver, message))
        logfile.close()
        return messageId
