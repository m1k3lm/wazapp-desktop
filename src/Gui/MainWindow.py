#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4.QtCore import Qt, pyqtSlot as Slot, pyqtSignal as Signal, QSettings
from PyQt4.QtGui import QMainWindow, QTabWidget

from ChatWidget import ChatWidget
from ContactsWidget import ContactsWidget


class MainWindow(QMainWindow):
    add_contact_signal = Signal(str, str)
    show_message_signal = Signal(str, float, str, str, str)
    send_message_signal = Signal(str, unicode)
    has_unread_message_signal = Signal(bool)

    def __init__(self, contacts, chatHistory):
        super(MainWindow, self).__init__()
        self._contacts = contacts
        self._chatHistory = chatHistory
        self._quit = False
        self._chatWidgets = {}
        self._unreadMessages = set()

        self._windowTitle = 'Yowsup Gui'
        self.setWindowTitle(self._windowTitle)
        self._chatWidgetDockArea = Qt.LeftDockWidgetArea
        self.setTabPosition(self._chatWidgetDockArea, QTabWidget.West)
        self.show_message_signal.connect(self.showMessage)

        self._contactsWidget = ContactsWidget()
        self.setCentralWidget(self._contactsWidget)
        self.add_contact_signal.connect(self._contactsWidget.addContact)
        self._contactsWidget.start_chat_signal.connect(self.getChatWidget)
        self._contactsWidget.import_google_contacts_signal.connect(self._contacts.importGoogleContacts)
        self._contactsWidget.update_contact_signal.connect(self._contacts.updateContact)
        self._contactsWidget.remove_contact_signal.connect(self._contacts.removeContact)

        self._contactsWidget.contactsUpdated(self._contacts.getContacts())
        self._contacts.contacts_updated_signal.connect(self._contactsWidget.contactsUpdated)
        self._contacts.contact_status_changed_signal.connect(self._contactsWidget.contactStatusChanged)
        self._contacts.edit_contact_signal.connect(self._contactsWidget.editContact)

        self._settings = QSettings('yowsup', 'gui')
        for conversationId in self._settings.value('mainWindow/openConversations').toStringList():
            self.getChatWidget(conversationId)
        self.restoreGeometry(self._settings.value('mainWindow/geometry').toByteArray());
        self.restoreState(self._settings.value('mainWindow/windowState').toByteArray());

    @Slot()
    def close(self):
        self._quit = True
        super(MainWindow, self).close()

    def closeEvent(self, event):
        if self._quit:
            self._settings.beginGroup('mainWindow')
            self._settings.setValue('geometry', self.saveGeometry())
            self._settings.setValue('windowState', self.saveState())
            self._settings.setValue('openConversations', self._chatWidgets.keys())
            self._settings.endGroup()
            event.accept()
        else:
            self.hide()
            event.ignore()

    @Slot(str, float, str, str, str)
    def showMessage(self, conversationId, timestamp, sender, receiver, message):
        self.getChatWidget(conversationId).showMessage(conversationId, timestamp, sender, receiver, message)

    @Slot(str, bool)
    def unreadMessage(self, conversationId, unread):
        if unread:
            self._unreadMessages.add(conversationId)
        else:
            self._unreadMessages.discard(conversationId)
        if len(self._unreadMessages) > 0:
            self.setWindowTitle('*' + self._windowTitle)
            self.has_unread_message_signal.emit(True)
        else:
            self.setWindowTitle(self._windowTitle)
            self.has_unread_message_signal.emit(False)

    def getChatWidget(self, conversationId):
        if conversationId not in self._chatWidgets:
            dockWidget = ChatWidget(conversationId, self._chatHistory, self._contacts)
            dockWidget.setObjectName(conversationId)
            dockWidget.setAllowedAreas(self._chatWidgetDockArea)

            for other in self._chatWidgets.values():
                # add new dockWidget tabified on top of the other non-floating dockWidgets
                if not other.isFloating():
                    self.tabifyDockWidget(other, dockWidget)
                    break
            else:
                # if no other non-floating dockWidgets were found, add this dockWidget to the dock area
                self.addDockWidget(self._chatWidgetDockArea, dockWidget)

            self._chatWidgets[conversationId] = dockWidget
            dockWidget.send_message_signal.connect(self.send_message_signal)
            dockWidget.has_unread_message_signal.connect(self.unreadMessage)

        # make sure dockWidget is visible and on top of others
        dockWidget = self._chatWidgets[conversationId]
        dockWidget.messageText.setFocus()
        dockWidget.show()
        dockWidget.raise_()
        return dockWidget
