#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import base64

from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import QObject, pyqtSlot as Slot, pyqtSignal as Signal
from helpers import CONTACTS_FILE, getConfig, readObjectFromFile, writeObjectToFile

from Yowsup.Contacts.contacts import WAContactsSyncRequest

class Contacts(QObject):
    contacts_updated_signal = Signal(dict)
    contact_status_changed_signal = Signal(str, dict)

    def __init__(self):
        super(Contacts, self).__init__()
        self._contactStatus = {}
        self._loadAliases()
        self.contacts_updated_signal.emit(self.getContacts())

    def _loadAliases(self):
        self.aliases = {}
        self.aliasesRev = {}
        if os.path.exists(CONTACTS_FILE):
            self.aliases = readObjectFromFile(CONTACTS_FILE)
            self.aliasesRev = dict([(val, key) for key, val in self.aliases.items()])

    def _saveAliases(self):
        writeObjectToFile(CONTACTS_FILE, self.aliases)

    def name2jid(self, name):
        if name in self.aliases:
            name = self.aliases[name]
        if name.startswith("#"):
            return "%s@g.us" % name[1:]
        else:
            return "%s@s.whatsapp.net" % name

    def jid2name(self, jid):
        name, server = jid.split("@")
        if server == "g.us":
            name = "#" + name
        if name in self.aliasesRev:
            name = self.aliasesRev[name]
        return name

    def getContacts(self):
        return dict([(name, self.name2jid(name)) for name in self.aliases.keys()])

    @Slot(str, object, object)
    def contactStatusChanged(self, conversationId, available, lastSeen):
        status = self._contactStatus.get(conversationId, {'available': False, 'lastSeen': 0})
        if available is not None:
            status['available'] = available
        if lastSeen is not None:
            status['lastSeen'] = lastSeen
        self._contactStatus[conversationId] = status
        self.contact_status_changed_signal.emit(conversationId, status)

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

        waUsername = str(getConfig('phone'))
        waPassword = base64.b64decode(getConfig('password'))
        waContactsSync = WAContactsSyncRequest(waUsername, waPassword, googleContacts.keys())
        results = waContactsSync.send()

        numWhatsAppUsers = 0
        for entry in results.get('c', []):
            hasWhatsApp = bool(entry['w'])
            if hasWhatsApp:
                name = googleContacts[entry['p']]
                number = entry['n']
                self.aliases[name] = number
                self.aliasesRev[number] = name
                numWhatsAppUsers += 1

        self._saveAliases()

        self.contacts_updated_signal.emit(self.getContacts())
        QMessageBox.information(None, 'Import successful', 'Found %d WhatsApp users in your %d Google contacts.' % (numWhatsAppUsers, len(googleContacts)))
