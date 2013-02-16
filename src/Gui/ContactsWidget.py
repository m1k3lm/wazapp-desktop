#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import datetime
import sip
sip.setapi('QString', 2)
from PyQt4.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt4.QtGui import QWidget, QListWidgetItem, QLineEdit, QInputDialog, QIcon
from PyQt4.uic import loadUi

class ContactsWidget(QWidget):
    start_chat_signal = Signal(str)
    import_google_conctacts_signal = Signal(str, str)

    def __init__(self, parent=None):
        super(ContactsWidget, self).__init__(parent)
        self._items = {}

        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ContactsWidget.ui')
        loadUi(ui_file, self)

    @Slot(dict)
    def contactsUpdated(self, contacts):
        self.contactList.clear()
        self._jidToListItem = {}
        for name, conversationId in contacts.items():
            self.addContact(name, conversationId)

    @Slot(str, str)
    def addContact(self, name, conversationId):
        item = QListWidgetItem(name)
        item._conversationId = conversationId
        self._items[conversationId] = item
        self.contactList.addItem(item)

    @Slot(str, dict)
    def contactStatusChanged(self, conversationId, status):
        item = self._items[conversationId]
        if status['available']:
            item.setIcon(QIcon.fromTheme('user-available'))
        else:
            item.setIcon(QIcon.fromTheme('user-offline'))
        formattedDate = datetime.datetime.fromtimestamp(status['lastSeen']).strftime('%d-%m-%Y %H:%M:%S')
        item.setToolTip('Available: %s (last seen %s)' % (status['available'], formattedDate))

    @Slot(QListWidgetItem)
    def on_contactList_itemDoubleClicked(self, item):
        self.start_chat_signal.emit(item._conversationId)

    @Slot()
    def on_importGoogleContactsButton_clicked(self):
        googleUsername, ok = QInputDialog.getText(self, 'Google Username', 'Enter your Google username/email')
        if not ok:
            return
        googlePassword, ok = QInputDialog.getText(self, 'Google Password', 'Enter your Google password', mode=QLineEdit.Password)
        if not ok:
            return
        self.import_google_conctacts_signal.emit(googleUsername, googlePassword)
