#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import datetime
import webbrowser

from PyQt4.QtCore import Qt, pyqtSlot as Slot, pyqtSignal as Signal
from PyQt4.QtGui import QWidget
from PyQt4.QtWebKit import QWebPage
from PyQt4.uic import loadUi

url_pattern1 = re.compile(r"(^|[\n ])(([\w]+?://[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
url_pattern2 = re.compile(r"(^|[\n ])(((www|ftp)\.[\w\#$%&~.\-;:=,?@\[\]+]*)(/[\w\#$%&~/.\-;:=,?@\[\]+]*)?)", re.IGNORECASE | re.DOTALL)
def url2link(text):
    text = url_pattern1.sub(r'\1<a href="\2" target="_blank">\2</a>', text)
    text = url_pattern2.sub(r'\1<a href="http:/\2" target="_blank">\2</a>', text)
    return text


class ChatWidget(QWidget):
    send_message_signal = Signal(str, str)
    scroll_to_bottom_signal = Signal()
    show_message_signal = Signal(str, float, str, str, str)

    def __init__(self, parent=None, conversationId=None):
        super(ChatWidget, self).__init__(parent)
        self._conversationId = conversationId

        path = os.path.dirname(os.path.realpath(__file__))
        ui_file = os.path.join(path, 'ChatWidget.ui')
        loadUi(ui_file, self)
        self.chatView.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.__on_messageText_keyPressEvent = self.messageText.keyPressEvent
        self.messageText.keyPressEvent = self.on_messageText_keyPressEvent
        self.scroll_to_bottom_signal.connect(self.on_scrollToBottom, Qt.QueuedConnection)
        self.show_message_signal.connect(self.showMessage, Qt.QueuedConnection)

        self._lastSender = ''
        self._lastDate = ''
        content_type = u'<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />'
        css_link = u'<link rel="stylesheet" type="text/css" href="file:///%s/ChatView.css">' % path.replace('\\', '/')
        html = u'<html><head>%s%s</head><body></body></html>' % (content_type, css_link)
        self.chatView.setHtml(html)
        self._bodyElement = self.chatView.page().mainFrame().documentElement().findFirst('body')

    def on_messageText_keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not bool(event.modifiers() & Qt.ShiftModifier):
            self.on_sendButton_clicked()
            event.accept()
        else:
            self.__on_messageText_keyPressEvent(event)

    def on_chatView_linkClicked(self, url):
        #print 'on_chatView_linkClicked():', url.toString()
        webbrowser.open(url.toString())

    @Slot()
    def on_scrollToBottom(self):
        self.chatView.page().mainFrame().setScrollBarValue(Qt.Vertical, self.chatView.page().mainFrame().scrollBarMaximum(Qt.Vertical))

    @Slot()
    def on_sendButton_clicked(self):
        message = self.messageText.toPlainText()
        self.messageText.clear()
        self.send_message_signal.emit(self._conversationId, message)

    @Slot(str, float, str, str, str)
    def showMessage(self, conversationId, timestamp, sender, receiver, message):
        if conversationId != self._conversationId:
            print 'showMessage(): message to "%s" not for me "%s"' % (conversationId, self._conversationId)
            return
        if len(message) > 0:
            formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%A, %d %B %Y')
            formattedTime = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            if self._lastDate != formattedDate:
                self._lastDate = formattedDate
                self._bodyElement.appendInside('<p class="date">%s</p>' % formattedDate)

            # don't show sender name again, if multiple consecutive messages from one sender
            if sender == self._lastSender:
                sender = '...'
            else:
                self._lastSender = sender

            # parse plain text messages for links
            if '</a>' not in message:
                message = url2link(message)

            # parse plain text messages for new lines
            if '<br>' not in message:
                message = u'<br>'.join(message.split('\n'))

            message = u'<p><span class="time">[%s]</span> <span class="name">%s:</span> <span class="message">%s</span></p>' % (formattedTime, sender, message)
            self._bodyElement.appendInside(message)
            self.scroll_to_bottom_signal.emit()
