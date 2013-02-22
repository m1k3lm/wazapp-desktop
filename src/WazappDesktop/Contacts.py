#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import base64
import re

from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import QObject, pyqtSlot as Slot, pyqtSignal as Signal
from helpers import CONTACTS_FILE, getConfig, readObjectFromFile, writeObjectToFile

from Yowsup.Contacts.contacts import WAContactsSyncRequest

class Contacts(QObject):
    contacts_updated_signal = Signal(dict)
    contact_status_changed_signal = Signal(str, dict)
    edit_contact_signal = Signal(str, str)
    userIdFormat = '%s@s.whatsapp.net'
    groupIdFormat = '%s@g.us'

    def __init__(self):
        super(Contacts, self).__init__()
        self._contactStatus = {}
        self._loadContacts()
        self.contacts_updated_signal.emit(self.getContacts())

    def _loadContacts(self):
        self._contacts = {}
        if os.path.exists(CONTACTS_FILE):
            self._contacts = readObjectFromFile(CONTACTS_FILE)

    def _saveContacts(self):
        writeObjectToFile(CONTACTS_FILE, self._contacts)

    def phoneToConversationId(self, phoneOrGroup):
        # if there is an @, it's got to be a jid already
        if '@' in phoneOrGroup:
            return phoneOrGroup
        # if there is exactly one - followed by 10 digits, it's got to be a group number
        if phoneOrGroup.count('-') == 1 and phoneOrGroup[-11] == '-':
            return self.groupIdFormat % phoneOrGroup
        # strip all non numeric chars
        phoneOrGroup = re.sub('[\D]+', '', phoneOrGroup)
        return self.userIdFormat % phoneOrGroup

    def jid2name(self, jid):
        return self._contacts.get(jid, jid)

    def getContacts(self):
        return self._contacts.copy()

    @Slot(str)
    def removeContact(self, conversationId):
        del self._contacts[conversationId]
        self._saveContacts()
        self.contacts_updated_signal.emit(self.getContacts())

    @Slot(str, str)
    def updateContact(self, name, phoneOrGroup):
        if phoneOrGroup.count('-') == 1 and phoneOrGroup[-11] == '-':
            phone = phoneOrGroup[:-11]
        else:
            phone = phoneOrGroup
        waPhones = self.getWAUsers([phone]).values()
        if len(waPhones) > 0:
            self._contacts[self.phoneToConversationId(waPhones[0])] = name
            self._saveContacts()
            self.contacts_updated_signal.emit(self.getContacts())
        else:
            text = 'WhatsApp did not know about the phone number "%s"!\n' % (phoneOrGroup)
            text += 'Please check that the number starts with a "+" and your country code.'
            QMessageBox.warning(None, 'WhatsApp User Not Found', text)
            self.edit_contact_signal.emit(name, phoneOrGroup)

    @Slot(str, object, object)
    def contactStatusChanged(self, conversationId, available, lastSeen):
        status = self._contactStatus.get(conversationId, {'available': False, 'lastSeen': 0})
        if available is not None:
            status['available'] = available
        if lastSeen is not None:
            status['lastSeen'] = lastSeen
        self._contactStatus[conversationId] = status
        self.contact_status_changed_signal.emit(conversationId, status)

    def getWAUsers(self, phoneNumbers):
        waUsername = str(getConfig('countryCode') + getConfig('phoneNumber'))
        waPassword = base64.b64decode(getConfig('password'))
        waContactsSync = WAContactsSyncRequest(waUsername, waPassword, phoneNumbers)
        results = waContactsSync.send()

        waUsers = {}
        for entry in results.get('c', []):
            hasWhatsApp = bool(entry['w'])
            if hasWhatsApp:
                requestedPhone = entry['p']
                phone = entry['n']
                waUsers[requestedPhone] = phone
        return waUsers

    @Slot(str, str)
    def importGoogleContacts(self, googleUsername, googlePassword):
        import gdata.contacts.client
        gd_client = gdata.contacts.client.ContactsClient(source='GoogleInc-ContactsPythonSample-1')
        try:
            gd_client.ClientLogin(googleUsername, googlePassword, gd_client.source)
        except gdata.client.BadAuthentication as e:
            QMessageBox.warning(None, 'Authentication Failure', 'Failed to authenticate with Google for user:\n%s\n\nError was:\n%s' % (googleUsername, e))
            return

        query = gdata.contacts.client.ContactsQuery()
        query.max_results = 10000

        googleContacts = {}
        feed = gd_client.GetContacts(q=query)
        for entry in feed.entry:
            for number in entry.phone_number:
                googleContacts[number.text] = entry.title.text

        waUsers = self.getWAUsers(googleContacts.keys())
        for googlePhone, waPhone in waUsers.items():
            name = googleContacts[googlePhone]
            self._contacts[self.phoneToConversationId(waPhone)] = name

        self._saveContacts()

        self.contacts_updated_signal.emit(self.getContacts())
        QMessageBox.information(None, 'Import successful', 'Found %d WhatsApp users in your %d Google contacts.' % (len(waUsers), len(googleContacts)))
