#!/usr/bin/python
# -*- coding: utf-8 -*-

import sip
sip.setapi('QString', 2)
from PyQt4.QtCore import Qt, pyqtSlot as Slot, pyqtSignal as Signal, QSettings
from PyQt4.QtGui import QMainWindow, QDockWidget, QTabWidget

from ChatWidget import ChatWidget
from ContactsWidget import ContactsWidget


class MainWindow(QMainWindow):
    add_contact_signal = Signal(str, str)
    show_message_signal = Signal(str, float, str, str, str)
    send_message_signal = Signal(str, str)

    def __init__(self, contacts, chatHistory):
        super(MainWindow, self).__init__()
        self._contacts = contacts
        self._chatHistory = chatHistory

        self._chatWidgets = {}
        self.setWindowTitle('WhatsApp')
        self._chatWidgetDockArea = Qt.LeftDockWidgetArea
        self.setTabPosition(self._chatWidgetDockArea, QTabWidget.West)
        self._contactsWidget = ContactsWidget()
        self.show_message_signal.connect(self.showMessage)
        self.add_contact_signal.connect(self._contactsWidget.addContact)
        self._contactsWidget.start_chat_signal.connect(self.getChatWidget)
        self.setCentralWidget(self._contactsWidget)

        for name in self._contacts.aliases:
            self.add_contact_signal.emit(name, self._contacts.name2jid(name))

        self._settings = QSettings('yowsup', 'gui')
        for conversationId in self._settings.value('mainWindow/openConversations').toStringList():
            self.getChatWidget(conversationId)
        self.restoreGeometry(self._settings.value('mainWindow/geometry').toByteArray());
        self.restoreState(self._settings.value('mainWindow/windowState').toByteArray());

    def closeEvent(self, event):
        self._settings.beginGroup('mainWindow')
        self._settings.setValue('geometry', self.saveGeometry())
        self._settings.setValue('windowState', self.saveState())
        self._settings.setValue('openConversations', self._chatWidgets.keys())
        self._settings.endGroup()
        super(MainWindow, self).closeEvent(event)

    @Slot(str, float, str, str, str)
    def showMessage(self, conversationId, timestamp, sender, receiver, message):
        self.getChatWidget(conversationId).showMessage(conversationId, timestamp, sender, receiver, message)

    def getChatWidget(self, conversationId):
        if conversationId not in self._chatWidgets:
            widget = ChatWidget(conversationId=conversationId)
            dockWidget = QDockWidget()
            dockWidget.setObjectName(conversationId)
            dockWidget.setWindowTitle(self._contacts.jid2name(conversationId))
            dockWidget.setAllowedAreas(self._chatWidgetDockArea)
            dockWidget.setWidget(widget)

            for other in self._chatWidgets.values():
                # add new dockWidget tabified on top of the other non-floating dockWidgets
                if not other.isFloating():
                    self.tabifyDockWidget(other, dockWidget)
                    break
            else:
                # if no other non-floating dockWidgets were found, add this dockWidget to the dock area
                self.addDockWidget(self._chatWidgetDockArea, dockWidget)

            self._chatWidgets[conversationId] = dockWidget
            widget.send_message_signal.connect(self.send_message_signal)

            # show last messages
            for line in self._chatHistory.get(conversationId)[-5:]:
                timestamp, sender, receiver, message = line
                widget.show_message_signal.emit(conversationId, timestamp, self._contacts.jid2name(sender), self._contacts.jid2name(receiver), message)

        # make sure dockWidget is visible and on top of others
        dockWidget = self._chatWidgets[conversationId]
        dockWidget.widget().messageText.setFocus()
        dockWidget.show()
        dockWidget.raise_()
        return dockWidget.widget()
