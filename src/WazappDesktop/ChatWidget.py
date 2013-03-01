#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import datetime
import time
import webbrowser

from PyQt4.QtCore import Qt, pyqtSlot as Slot, pyqtSignal as Signal, QPoint, QDir, QUrl, QTimer
from PyQt4.QtGui import QDockWidget, QMenu, QIcon, QCursor
from PyQt4.QtWebKit import QWebPage, QWebElement
from PyQt4.uic import loadUi

from .helpers import getConfig
from .Contacts import Contacts
from .ChatHistory import ChatHistory

url_pattern1 = re.compile(r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
url_pattern2 = re.compile(r"(^|[\n ])(((www|ftp)\.[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
def url2link(text):
    text = url_pattern1.sub(r'\1<a href="\2" target="_blank">\2</a>', text)
    text = url_pattern2.sub(r'\1<a href="http:/\2" target="_blank">\2</a>', text)
    return text


class ChatWidget(QDockWidget):
    send_message_signal = Signal(str, unicode)
    scroll_to_bottom_signal = Signal()
    show_message_signal = Signal(str, str, float, str, str, str)
    show_history_message_signal = Signal(str, str, float, str, str, str, bool)
    show_history_since_signal = Signal(float)
    show_history_num_messages_signal = Signal(int)
    has_unread_message_signal = Signal(str, bool)
    edit_contact_signal = Signal(str, str)
    paragraphIdFormat = 'p%s'

    def __init__(self, conversationId):
        super(ChatWidget, self).__init__()
        self._conversationId = conversationId
        self._windowTitle = Contacts.instance().jid2name(self._conversationId)
        self._ownJid = Contacts.instance().phoneToConversationId(getConfig('countryCode') + getConfig('phoneNumber'))
        self._bodyElement = QWebElement()
        self._scrollTimer = QTimer()
        self._scrollTimer.setSingleShot(True)
        self._scrollTimer.timeout.connect(self.on_scrollToBottom)
        self.scroll_to_bottom_signal.connect(self.on_scrollToBottom, Qt.QueuedConnection)

        loadUi(os.path.join(QDir.searchPaths('ui')[0], 'ChatWidget.ui'), self)
        self.chatView.load(QUrl('file:///%s/ChatView.html' % QDir.searchPaths('html')[0]))

        self.historyButton.setIcon(QIcon.fromTheme('clock'))

        self.setWindowTitle(self._windowTitle)

        self.visibilityChanged.connect(self.on_visibilityChanged)
        self.chatView.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.__on_messageText_keyPressEvent = self.messageText.keyPressEvent
        self.messageText.keyPressEvent = self.on_messageText_keyPressEvent
        self.show_message_signal.connect(self.showMessage)
        self.show_history_message_signal.connect(self.showMessage)
        self.show_history_since_signal.connect(self.showHistorySince)
        self.show_history_num_messages_signal.connect(self.showHistoryNumMessages)
        self.has_unread_message_signal.connect(self.unreadMessage)

        self.showHistorySince(datetime.date.today(), minMessage=3, maxMessages=10)

    def on_chatView_customContextMenuRequested(self, pos):
        menu = QMenu()
        results = {}
        results[menu.addAction('Dump HTML')] = self.dumpHtml
        result = menu.exec_(self.chatView.mapToGlobal(pos))
        if result in results:
            results[result]()

    def dumpHtml(self):
        print self.chatView.page().mainFrame().toHtml()

    def on_visibilityChanged(self, visible):
        if visible:
            self.has_unread_message_signal.emit(self._conversationId, False)
            self.messageText.setFocus(Qt.OtherFocusReason)

    @Slot()
    def on_historyButton_pressed(self):
        menu = QMenu()
        results = {
            menu.addAction('Today'): datetime.date.today(),
            menu.addAction('Last 24 Hours'): datetime.datetime.now() - datetime.timedelta(1),
            menu.addAction('Last 7 Days'): datetime.datetime.now() - datetime.timedelta(7),
            menu.addAction('Last 30 Days'): datetime.datetime.now() - datetime.timedelta(30),
            menu.addAction('Last 6 Month'): datetime.datetime.now() - datetime.timedelta(30 * 6),
            menu.addAction('Last Year'): datetime.datetime.now() - datetime.timedelta(365),
            menu.addAction('All Time'): 0,
            menu.addAction('None'): datetime.datetime.now(),
        }
        result = menu.exec_(self.historyButton.mapToGlobal(QPoint(0, self.historyButton.height())))
        if result in results:
            self.showHistorySince(results[result])

    @Slot(float)
    @Slot(datetime.date)
    @Slot(datetime.datetime)
    def showHistorySince(self, timestamp, minMessage=0, maxMessages=10000):
        if type(timestamp) in (datetime.datetime, datetime.date):
            timestamp = time.mktime(timestamp.timetuple())
        history = ChatHistory.instance().get(self._conversationId)
        timestampIndex = ChatHistory.instance().dataFields.index('timestamp')
        for index, data in enumerate(history['list']):
            if timestamp <= data[timestampIndex]:
                numMessages = len(history['list']) - index
                break
        else:
            numMessages = 0
        self.showHistoryNumMessages(min(max(minMessage, numMessages), maxMessages))

    @Slot(int)
    def showHistoryNumMessages(self, numMessages):
        #print numMessages, self._conversationId
        self.clearChatView()
        # queue showing of messages until page is loaded
        self._showNumMessages = numMessages
        if self._bodyElement.isNull():
            return
        self._showHistoryMessages()

    def _showHistoryMessages(self):
        if self._bodyElement.isNull():
            print '_showHistoryMessages(): bodyElement is Null!'
            return
        # show last messages
        if self._showNumMessages > 0:
            for data in ChatHistory.instance().get(self._conversationId)['list'][-self._showNumMessages:]:
                messageId, timestamp, sender, receiver, message = data
                self.show_history_message_signal.emit(self._conversationId, messageId, timestamp, sender, receiver, message, False)
            self._showNumMessages = 0

    def clearChatView(self):
        self._lastSender = ''
        self._lastDate = ''
        self._showNumMessages = 0
        self._bodyElement.setInnerXml('')

    @Slot()
    @Slot(bool)
    def on_chatView_loadFinished(self, ok=True):
        self._bodyElement = self.chatView.page().mainFrame().documentElement().findFirst('body')
        # check that the body element is really loaded, otherwise try again later
        if self._bodyElement.isNull():
            QTimer.singleShot(100, self.on_chatView_loadFinished)
            return
        self._showHistoryMessages()

    @Slot(str, bool)
    def unreadMessage(self, conversationId, unread):
        if unread:
            self.setWindowTitle('*' + self._windowTitle)
        else:
            self.setWindowTitle(self._windowTitle)

    def on_messageText_keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not bool(event.modifiers() & Qt.ShiftModifier):
            self.on_sendButton_clicked()
            event.accept()
        else:
            self.__on_messageText_keyPressEvent(event)

    def on_command_contactMenu(self, parameters):
        conversationId = parameters.get('jid')
        if conversationId is None:
            print 'on_command_contactMenu(): missing parameter "jid"'
            return
        knownContact = len(parameters.get('name', '')) > 0
        menu = QMenu()
        results = {
            menu.addAction('Edit Contact' if knownContact else 'Add Contact'): (self.edit_contact_signal.emit, (parameters.get('name', ''), parameters['jid'])),
        }
        result = menu.exec_(QCursor.pos())
        if result in results:
            results[result][0](*results[result][1])


    def on_chatView_linkClicked(self, url):
        if url.scheme() == 'wa':
            command = url.path()
            parameters = dict(url.queryItems())
            handler = getattr(self, 'on_command_%s' % command)
            if handler is None:
                print 'on_chatView_linkClicked(): unknown command: %s' % (command)
            else:
                handler(parameters)
        else:
            webbrowser.open(url.toString())

    @Slot()
    def on_scrollToBottom(self):
        bottom = self.chatView.page().mainFrame().scrollBarMaximum(Qt.Vertical)
        self.chatView.page().mainFrame().setScrollBarValue(Qt.Vertical, bottom)

    @Slot()
    def on_sendButton_clicked(self):
        message = self.messageText.toPlainText()
        self.messageText.clear()
        self.send_message_signal.emit(self._conversationId, message)

    @Slot(str, float, str, str, str)
    @Slot(str, float, str, str, str, bool)
    def showMessage(self, conversationId, messageId, timestamp, senderJid, receiver, message, isNewMessage=True):
        if len(message) == 0:
            return
        # make sure this message goes in the right chat view
        if conversationId != self._conversationId:
            print 'showMessage(): message to "%s" not for me "%s"' % (conversationId, self._conversationId)
            return
        # if html page is not loaded yet, queue this message
        if self._bodyElement.isNull():
            self._showNumMessages += 1
            return

        formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%A, %d %B %Y')
        formattedTime = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        if self._lastDate != formattedDate:
            self._lastDate = formattedDate
            self._bodyElement.appendInside('<p class="date">%s</p>' % formattedDate)

        senderName = Contacts.instance().jid2name(senderJid)
        senderDisplayName = senderName

        # set class for name element, depending if senderJid is in contacts and if its or own jid
        if senderJid == senderName:
            senderDisplayName = senderName.split('@')[0]
            senderName = ''
            nameClass = 'unknown'
        elif senderJid == self._ownJid:
            nameClass = 'myname'
        else:
            nameClass = 'name'

        # don't show sender name again, if multiple consecutive messages from one sender
        if senderDisplayName == self._lastSender:
            senderDisplayName = '...'
        else:
            self._lastSender = senderDisplayName

        # parse plain text messages for links
        if '</a>' not in message:
            message = url2link(message)

        # parse plain text messages for new lines
        if '<br>' not in message:
            message = u'<br>'.join(message.split('\n'))

        paragraphId = self.paragraphIdFormat % messageId
        paragraph = u'<p id=%s>' % paragraphId
        paragraph += '<span class="time">[%s] </span>' % formattedTime
        paragraph += '<a href="wa:contactMenu?jid=%s&name=%s" class="%s">%s: </a>' % (senderJid, senderName, nameClass, senderDisplayName)
        paragraph += '<span class="message">%s</span></p>' % message
        self._bodyElement.appendInside(paragraph)

        self.chatView.page().mainFrame().evaluateJavaScript('elementAdded("%s"); null' % paragraphId)

        # set scroll timer to scroll down in 100ms, after the new text is hopefully rendered (any better solutions?)
        self._scrollTimer.start(100)

        if isNewMessage and not (self.isVisible() and self.isActiveWindow()):
            self.has_unread_message_signal.emit(self._conversationId, True)

    @Slot(str, str, str)
    def messageStatusChanged(self, conversationId, messageId, status):
        paragraphId = self.paragraphIdFormat % messageId
        messageElement = self._bodyElement.findFirst('p#%s' % paragraphId)
        if not messageElement.isNull():
            messageElement.setAttribute('class', status)
