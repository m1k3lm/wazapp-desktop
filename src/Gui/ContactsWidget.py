#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sip
sip.setapi('QString', 2)
from PyQt4.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt4.QtGui import QWidget, QListWidgetItem, QLineEdit, QInputDialog
from PyQt4.uic import loadUi


class ContactsWidget(QWidget):
    start_chat_signal = Signal(str)
    import_google_conctacts_signal = Signal(str, str)

    def __init__(self, parent=None):
        super(ContactsWidget, self).__init__(parent)

        ui_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ContactsWidget.ui')
        loadUi(ui_file, self)

    @Slot(dict)
    def contactsUpdated(self, contacts):
        self.contactList.clear()
        for name, conversationId in contacts.items():
            self.addContact(name, conversationId)

    @Slot(str, str)
    def addContact(self, name, conversationId):
        item = QListWidgetItem(name)
        item._conversationId = conversationId
        self.contactList.addItem(item)

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
