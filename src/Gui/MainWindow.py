#!/usr/bin/python
# -*- coding: utf-8 -*-

from PyQt4.QtCore import Qt, pyqtSlot as Slot, pyqtSignal as Signal, QSettings
from PyQt4.QtGui import QMainWindow, QTabWidget

from ChatWidget import ChatWidget
from ContactsWidget import ContactsWidget


class MainWindow(QMainWindow):
    add_contact_signal = Signal(str, str)
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

        self._contactsWidget = ContactsWidget()
        self.setCentralWidget(self._contactsWidget)
        self.add_contact_signal.connect(self._contactsWidget.addContact)
        self._contactsWidget.start_chat_signal.connect(self.startChat)
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

    @Slot(str)
    def startChat(self, conversationId):
        # retrieve or create dockWidget for this conversationId
        dockWidget = self.getChatWidget(conversationId)
        # raise dockWidget in front of other dockWidgets
        dockWidget.raise_()

    @Slot(str, str, float, str, str, str)
    def showMessage(self, conversationId, messageId, timestamp, sender, receiver, message):
        dockWidget = self.getChatWidget(conversationId)

        # move dockWidget to the top of the tab list and restore the focus of the currently active tab
        focusedDockWidget = dockWidget
        for other in self.tabifiedDockWidgets(dockWidget):
            if other.hasFocus():
                focusedDockWidget = other
            self.tabifyDockWidget(dockWidget, other)
        focusedDockWidget.raise_()

        dockWidget.showMessage(conversationId, messageId, timestamp, sender, receiver, message)

    @Slot(str, str, str)
    def messageStatusChanged(self, conversationId, messageId, status):
        self.getChatWidget(conversationId).messageStatusChanged(conversationId, messageId, status)

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
        # if no dockWidget for this conversationId exists, create a new one
        if conversationId not in self._chatWidgets:
            dockWidget = ChatWidget(conversationId, self._chatHistory, self._contacts)
            dockWidget.setObjectName(conversationId)
            dockWidget.setAllowedAreas(self._chatWidgetDockArea)

            for other in self._chatWidgets.values():
                if not other.isFloating():
                    # add new dockWidget tabified with the other dockWidgets
                    self.tabifyDockWidget(other, dockWidget)
                    break
            else:
                # if no other non-floating dockWidgets were found, add this dockWidget to the dock area
                self.addDockWidget(self._chatWidgetDockArea, dockWidget)

            self._chatWidgets[conversationId] = dockWidget
            dockWidget.send_message_signal.connect(self.send_message_signal)
            dockWidget.has_unread_message_signal.connect(self.unreadMessage)

        dockWidget = self._chatWidgets[conversationId]
        dockWidget.show()
        return dockWidget
