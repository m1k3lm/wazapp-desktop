#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import datetime

from PyQt4.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt4.QtGui import QWidget, QListWidgetItem, QLineEdit, QInputDialog, QIcon, QMenu
from PyQt4.uic import loadUi

from helpers import getConfig, setConfig

class ListWidgetItem(QListWidgetItem):

    def __lt__(self, otherItem):
        return self._sortingValue.lower() < otherItem._sortingValue.lower()

    def setOnline(self, online=True):
        if online:
            self.setIcon(QIcon.fromTheme('user-available'))
            self._sortingValue = ' ' + self.text()
        else:
            self.setIcon(QIcon.fromTheme('user-offline'))
            self._sortingValue = self.text()

    def setOffline(self):
        self.setOnline(False)

    def setUnknown(self):
        self.setIcon(QIcon.fromTheme('dialog-question'))
        self._sortingValue = '~' + self.text()

class ContactsWidget(QWidget):
    start_chat_signal = Signal(str)
    import_google_contacts_signal = Signal(str, str)
    update_contact_signal = Signal(str, str)
    remove_contact_signal = Signal(str)

    def __init__(self):
        super(ContactsWidget, self).__init__()
        self._items = {}

        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ContactsWidget.ui')
        loadUi(ui_file, self)

        self.importGoogleContactsButton.setIcon(QIcon.fromTheme('browser-download'))
        self.addContactButton.setIcon(QIcon.fromTheme('add'))

    def on_contactList_customContextMenuRequested(self, pos):
        item = self.contactList.itemAt(pos)
        if item is None:
            return
        menu = QMenu()
        results = {}
        results[menu.addAction('Edit Contact')] = self.editContact
        results[menu.addAction('Remove Contact')] = self.removeContact
        result = menu.exec_(self.contactList.mapToGlobal(pos))
        if result in results:
            results[result](item.text(), item._conversationId)

    def removeContact(self, name, conversationId):
        self.remove_contact_signal.emit(conversationId)

    @Slot()
    @Slot(str, str)
    def editContact(self, name='', conversationId=''):
        phone = conversationId.split('@')[0]
        if len(phone) == 0 or phone[0] != '+':
            phone = '+' + phone
        name, ok = QInputDialog.getText(self, 'Contact Name', 'Enter this contact\'s name', text=name)
        if not ok:
            return
        phone, ok = QInputDialog.getText(self, 'Contact Phone', 'Enter this contact\'s phone number\n(leading with a "+" and your country code)', text=phone)
        if not ok:
            return
        self.update_contact_signal.emit(name, phone)

    @Slot(dict)
    def contactsUpdated(self, contacts):
        self.contactList.clear()
        self._items = {}
        for conversationId, name in contacts.items():
            self.addContact(name, conversationId)

    @Slot()
    def on_addContactButton_clicked(self):
        self.editContact()

    @Slot(str, str)
    def addContact(self, name, conversationId):
        item = ListWidgetItem(name)
        item._conversationId = conversationId
        item.setUnknown()
        phone = conversationId.split('@')[0]
        item.setToolTip('Phone: +%s\nno information available (is this really a WhatApp user)' % (phone))
        self._items[conversationId] = item
        self.contactList.addItem(item)

    @Slot(str, dict)
    def contactStatusChanged(self, conversationId, status):
        if conversationId in self._items:
            item = self._items[conversationId]
            item.setOnline(status['available'])
            formattedDate = datetime.datetime.fromtimestamp(status['lastSeen']).strftime('%d-%m-%Y %H:%M:%S')
            phone = conversationId.split('@')[0]
            item.setToolTip('Phone: +%s\nAvailable: %s (last seen %s)' % (phone, status['available'], formattedDate))
        else:
            print 'received contact status for unknown contact:', conversationId

    @Slot(QListWidgetItem)
    def on_contactList_itemDoubleClicked(self, item):
        self.start_chat_signal.emit(item._conversationId)

    @Slot()
    def on_importGoogleContactsButton_clicked(self):
        googleUsername, ok = QInputDialog.getText(self, 'Google Username', 'Enter your Google username/email', text=getConfig('googleUsername', ''))
        if not ok:
            return
        googlePassword, ok = QInputDialog.getText(self, 'Google Password', 'Enter your Google password', mode=QLineEdit.Password)
        if not ok:
            return
        setConfig('googleUsername', googleUsername)
        self.import_google_contacts_signal.emit(googleUsername, googlePassword)
