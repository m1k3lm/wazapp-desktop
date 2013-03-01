#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import datetime
import base64
import cgi

from PyQt4.QtCore import pyqtSlot as Slot, pyqtSignal as Signal, QObject

from .MainWindow import MainWindow
from .SystemTrayIcon import SystemTrayIcon
from .Contacts import Contacts
from .ChatHistory import ChatHistory
from .helpers import makeHtmlImageLink, getConfig
from .Events import Events
from .PictureDownloader import PictureDownloader

from Yowsup.connectionmanager import YowsupConnectionManager

class WazappDesktop(QObject, Events):
    show_message_signal = Signal(str, str, float, str, str, str)
    contact_status_changed_signal = Signal(str, object, object)
    status_changed_signal = Signal(bool, bool)
    message_status_changed_signal = Signal(str, str, str)

    def __init__(self):
        super(WazappDesktop, self).__init__()
        Contacts.instance().contacts_updated_signal.connect(self.checkPresence)
        self.contact_status_changed_signal.connect(Contacts.instance().contactStatusChanged)

        self._hasUnreadMessage = False
        self._isOnline = False

        self._mainWindow = MainWindow()
        self.show = self._mainWindow.show
        self._mainWindow.send_message_signal.connect(self.do_send)
        self._mainWindow.has_unread_message_signal.connect(self.unreadMessage)

        self._systrayIcon = SystemTrayIcon()
        self._systrayIcon.quit_signal.connect(self.close)
        self._systrayIcon.quit_signal.connect(self._mainWindow.close)
        self._systrayIcon.toggle_main_window_signal.connect(self.toggleMainWindow)
        self.status_changed_signal.connect(self._systrayIcon.statusChanged)

        self.show_message_signal.connect(self._mainWindow.showMessage)
        self.message_status_changed_signal.connect(self._mainWindow.messageStatusChanged)

        self._ownJid = Contacts.instance().phoneToConversationId(getConfig('countryCode') + getConfig('phoneNumber'))

        connectionManager = YowsupConnectionManager()
        connectionManager.setAutoPong(True)

        self._pictureDownloader = PictureDownloader(connectionManager, Contacts.instance())

        self.signalsInterface = connectionManager.getSignalsInterface()
        self.methodsInterface = connectionManager.getMethodsInterface()
        for method, events in self.getEventBindings().iteritems():
            for event in events:
                self.signalsInterface.registerListener(event, method)

        self.setOnline(False)
        self._login()

    @Slot()
    def close(self):
        self._pictureDownloader.close()
        self.methodsInterface.call('presence_sendUnavailable')

    def _login(self):
        self.username = getConfig('countryCode') + getConfig('phoneNumber')
        try:
            password = base64.b64decode(getConfig('password'))
        except TypeError as e:
            print 'cannot login: error using stored password: %s' % e
            return
        self.methodsInterface.call('auth_login', (self.username, password))

    @Slot(bool)
    def unreadMessage(self, unread):
        self._hasUnreadMessage = unread
        self.status_changed_signal.emit(self._isOnline, self._hasUnreadMessage)

    def setOnline(self, online):
        self._isOnline = online
        self.status_changed_signal.emit(self._isOnline, self._hasUnreadMessage)

    @Slot()
    def toggleMainWindow(self):
        self._mainWindow.setVisible(not self._mainWindow.isVisible())

    @Slot(dict)
    def checkPresence(self, contacts):
        self.methodsInterface.call('picture_getIds', (','.join(contacts.keys()),))
        for jid in contacts.keys():
            self.methodsInterface.call('presence_request', (jid,))

    def handleMessage(self, messageId, timestamp, sender, receiver, message):
        if receiver == self._ownJid:
            conversationId = sender
        else:
            conversationId = receiver
        if type(message) is str:
            message = message.decode('utf8')
        #self._out('%s -> %s: %s' % (Contacts.instance().jid2name(sender), Contacts.instance().jid2name(receiver), message), timestamp=timestamp, logId=conversationId)
        messageId = ChatHistory.instance().add(conversationId, messageId, timestamp, sender, receiver, message)
        if messageId is not None:
            self.show_message_signal.emit(conversationId, messageId, timestamp, sender, receiver, message)

    @Slot(str, unicode)
    def do_send(self, receiver, message):
        messageId = self.methodsInterface.call('message_send', (receiver, message.encode('utf8')))
        self.handleMessage(messageId, time.time(), self._ownJid, receiver, cgi.escape(message))

    def _out(self, message, timestamp=None, logId='system'):
        if timestamp is None:
            timestamp = time.time()
        formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
        message = u'[%s] %s' % (formattedDate, message)
        print u'\n' + message

    def do_group_invite(self, groupJid, userJid):
        self.methodsInterface.call('group_addParticipant', (groupJid, userJid))

    def do_group_kick(self, groupJid, userJid):
        self.methodsInterface.call('group_removeParticipant', (groupJid, userJid))

    def do_group_create(self, subject):
        self.methodsInterface.call('group_create', (subject,))

    def do_group_destroy(self, groupJid):
        self.methodsInterface.call('group_end', (groupJid,))

    def do_group_subject(self, groupJid, subject):
        self.methodsInterface.call('group_subject', (groupJid, subject))

    def do_group_members(self, groupJid):
        self.methodsInterface.call('group_getParticipants', (groupJid,))

    @Events.bind('message_received')
    def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName):
        self.handleMessage(messageId, timestamp, jid, self._ownJid, cgi.escape(messageContent))
        if wantsReceipt:
            self.methodsInterface.call('message_ack', (jid, messageId))

    @Events.bind('group_messageReceived')
    def onGroupMessageReceived(self, messageId, groupJid, author, messageContent, timestamp, wantsReceipt, pushName):
        self.handleMessage(messageId, timestamp, author, groupJid, cgi.escape(messageContent))
        if wantsReceipt:
            self.methodsInterface.call('message_ack', (groupJid, messageId))

    @Events.bind('receipt_messageSent')
    def onMessageSent(self, jid, messageId):
        #print 'onMessageSent():', jid, messageId
        self.message_status_changed_signal.emit(jid, messageId, 'sent')

    @Events.bind('receipt_messageDelivered')
    def onMessageDelivered(self, jid, messageId):
        #print 'onMessageDelivered():', jid, messageId
        self.message_status_changed_signal.emit(jid, messageId, 'delivered')

    @Events.bind('group_gotInfo')
    def onGroupInfo(self, groupJid, owner, subject, subjectOwner, subjectTimestamp, creationTimestamp):
        creationTimestamp = datetime.datetime.fromtimestamp(creationTimestamp).strftime('%d-%m-%Y %H:%M')
        subjectTimestamp = datetime.datetime.fromtimestamp(subjectTimestamp).strftime('%d-%m-%Y %H:%M')
        self._out('Information on group %s: created by %s at %s, subject "%s" set by %s at %s' % (Contacts.instance().jid2name(groupJid), Contacts.instance().jid2name(owner), creationTimestamp, subject, Contacts.instance().jid2name(subjectOwner), subjectTimestamp), logId=groupJid)

    @Events.bind('group_createSuccess')
    def onGroupCreated(self, jid, groupJid):
        groupJid = '%s@%s' % (groupJid, jid)
        self._out('New group: %s' % Contacts.instance().jid2name(groupJid), logId=groupJid)

    @Events.bind('group_endSuccess')
    def onGroupDestroyed(self, jid):
        pass #jid contains only 'g.us' ????

    @Events.bind('group_subjectReceived')
    def onGroupSubjectReceived(self, messageId, groupJid, author, subject, timestamp, wantsReceipt):
        self.handleMessage(messageId, timestamp, author, groupJid, 'changed group subject to: "%s"' % subject)
        if wantsReceipt:
            self.methodsInterface.call('subject_ack', (groupJid, messageId))

    @Events.bind('group_gotParticipants')
    def onGroupGotParticipants(self, groupJid, participants):
        self.handleMessage(str(time.time()), time.time(), groupJid, groupJid, 'group participants are: "%s"' % participants)


    @Events.bind('image_received')
    def onImageReceived(self, messageId, jid, timestamp, preview, url, size, receiptRequested):
        self.handleImageReceived(messageId, timestamp, jid, self._ownJid, jid, preview, url, size, receiptRequested)

    @Events.bind('group_imageReceived')
    def onGroupImageReceived(self, messageId, groupJid, timestamp, author, preview, url, size, receiptRequested):
        self.handleImageReceived(messageId, timestamp, author, groupJid, groupJid, preview, url, size, receiptRequested)

    def handleImageReceived(self, messageId, timestamp, sender, receiver, ack, preview, url, size, receiptRequested):
        self.handleMessage(messageId, timestamp, sender, receiver, 'sent an image:<br>%s' % makeHtmlImageLink(preview, url))
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (ack, messageId))


    @Events.bind('video_received')
    def onVideoReceived(self, messageId, jid, timestamp, preview, url, size, receiptRequested):
        self.handleVideoReceived(messageId, timestamp, jid, self._ownJid, jid, preview, url, size, receiptRequested)

    @Events.bind('group_videoReceived')
    def onGroupVideoReceived(self, messageId, groupJid, timestamp, author, preview, url, size, receiptRequested):
        self.handleVideoReceived(messageId, timestamp, author, groupJid, groupJid, preview, url, size, receiptRequested)

    def handleVideoReceived(self, messageId, timestamp, sender, receiver, ack, preview, url, size, receiptRequested):
        self.handleMessage(messageId, timestamp, sender, receiver, 'sent a video: %s' % makeHtmlImageLink(preview, url))
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (ack, messageId))


    @Events.bind('audio_received')
    def onAudioReceived(self, messageId, jid, timestamp, url, size, receiptRequested):
        self.handleAudioReceived(messageId, timestamp, jid, self._ownJid, jid, url, size, receiptRequested)

    @Events.bind('group_audioReceived')
    def onGroupAudioReceived(self, messageId, groupJid, timestamp, author, url, size, receiptRequested):
        self.handleAudioReceived(messageId, timestamp, author, groupJid, groupJid, url, size, receiptRequested)

    def handleAudioReceived(self, messageId, timestamp, sender, receiver, ack, url, size, receiptRequested):
        self.handleMessage(messageId, timestamp, sender, receiver, 'sent an audio recording: %s' % url)
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (ack, messageId))


    @Events.bind('location_received')
    def onLocationReceived(self, messageId, jid, timestamp, name, preview, latitude, longitude, receiptRequested):
        self.handleLocationReceived(messageId, timestamp, jid, self._ownJid, jid, name, preview, latitude, longitude, receiptRequested)

    @Events.bind('group_locationReceived')
    def onGroupLocationReceived(self, messageId, groupJid, timestamp, author, name, preview, latitude, longitude, receiptRequested):
        self.handleLocationReceived(messageId, timestamp, author, groupJid, groupJid, name, preview, latitude, longitude, receiptRequested)

    def handleLocationReceived(self, messageId, timestamp, sender, receiver, ack, name, preview, latitude, longitude, receiptRequested):
        self.handleMessage(messageId, timestamp, sender, receiver, 'sent a location: "%s" (lat: %f, long: %f)' % (name, latitude, longitude))
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (ack, messageId))


    @Events.bind('vcard_received')
    def onVCardReceived(self, messageId, jid, timestamp, name, data, receiptRequested):
        self.handleVCardReceived(messageId, timestamp, jid, self._ownJid, jid, name, data, receiptRequested)

    @Events.bind('group_vcardReceived')
    def onGroupVCardReceived(self, messageId, groupJid, timestamp, author, name, data, receiptRequested):
        self.handleVCardReceived(messageId, timestamp, author, groupJid, groupJid, name, data, receiptRequested)

    def handleVCardReceived(self, messageId, timestamp, sender, receiver, ack, name, data, receiptRequested):
        self.handleMessage(messageId, timestamp, sender, receiver, 'sent a business card: "%s"\n%s' % (name, data))
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (ack, messageId))


    @Events.bind('notification_groupParticipantAdded')
    def onGroupParticipantAdded(self, groupJid, jid, author, timestamp, messageId, receiptRequested):
        self.handleMessage(messageId, timestamp, author, groupJid, 'added group member: "%s"' % (jid))
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (groupJid, messageId))

    @Events.bind('notification_groupParticipantRemoved')
    def onGroupParticipantRemoved(self, groupJid, jid, author, timestamp, messageId, receiptRequested):
        self.handleMessage(messageId, timestamp, author, groupJid, 'removed group member: "%s"' % (jid))
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (groupJid, messageId))

    @Events.bind('notification_contactProfilePictureUpdated')
    def onContactProfilePictureUpdated(self, jid, timestamp, messageId, receiptRequested):
        self._out('%s updated his contact picture' % Contacts.instance().jid2name(jid), timestamp, logId=jid)
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (jid, messageId))

    @Events.bind('notification_groupPictureUpdated')
    def onGroupPictureUpdated(self, groupJid, author, timestamp, messageId, receiptRequested):
        self._out('%s updated the picture for group %s' % (Contacts.instance().jid2name(author), Contacts.instance().jid2name(groupJid)), timestamp, logId=groupJid)
        if receiptRequested:
            self.methodsInterface.call('notification_ack', (groupJid, messageId))

    @Events.bind('auth_success')
    def onAuthSuccess(self, username):
        self._out('Logged in as %s' % username)
        self.setOnline(True)
        self.methodsInterface.call('ready')
        self.methodsInterface.call('presence_sendAvailable')
        self.checkPresence(Contacts.instance().getContacts())

    @Events.bind('auth_fail')
    def onAuthFailed(self, username, err):
        self._out('Auth Failed!')
        self.setOnline(False)

    @Events.bind('disconnected')
    def onDisconnected(self, reason):
        self._out('Disconnected because %s' % reason)
        self.setOnline(False)
        time.sleep(1)
        try:
            self._login()
        except:
            pass

    @Events.bind('presence_available')
    def onPresenceAvailable(self, jid):
        #self._out('%s is now available' % Contacts.instance().jid2name(jid))
        self.contact_status_changed_signal.emit(jid, True, time.time())

    @Events.bind('presence_unavailable')
    def onPresenceUnavailable(self, jid):
        #self._out('%s is now unavailable' % Contacts.instance().jid2name(jid))
        self.contact_status_changed_signal.emit(jid, False, None)

    @Events.bind('presence_updated')
    def onPresenceUpdated(self, jid, lastseen):
        #self._out('%s was last seen %s seconds ago' % (Contacts.instance().jid2name(jid), lastseen), logId=jid)
        self.contact_status_changed_signal.emit(jid, None, time.time() - lastseen)
