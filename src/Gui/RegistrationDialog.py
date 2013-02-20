#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re

from PyQt4.QtCore import pyqtSlot as Slot, QDir
from PyQt4.QtGui import QDialog, QMessageBox
from PyQt4.uic import loadUi

from helpers import getConfig, setConfig

from Yowsup.Common.utilities import Utilities
from Yowsup.Registration.v2.coderequest import WACodeRequest as WACodeRequestV2
from Yowsup.Registration.v2.regrequest import WARegRequest as WARegRequestV2

class RegistrationDialog(QDialog):
    _identity = '0000000000'

    def __init__(self):
        super(RegistrationDialog, self).__init__()
        loadUi(os.path.join(QDir.searchPaths('ui')[0], 'RegistrationDialog.ui'), self)

        self.countryCodeEdit.setText(getConfig('countryCode', ''))
        self.phoneNumberEdit.setText(getConfig('phoneNumber', ''))
        self._enableRegistration(self._hasValidPhone())

        password = getConfig('password', '')
        self.passwordEdit.setText(password)
        self._passwordChanged()

    def _passwordChanged(self):
        hasPassword = self._checkPasswordEdit()
        self.registerRadio.setChecked(not hasPassword)
        self.hasPasswordRadio.setChecked(hasPassword)
        self.registerRadio.toggled.emit(not hasPassword)
        self.hasPasswordRadio.toggled.emit(hasPassword)
        self.registerButton.setEnabled(len(self.registrationCodeEdit.text()) > 0)

    def _getPhone(self):
        countryCode = re.sub('[\D]+', '', self.countryCodeEdit.text()).lstrip('0')
        phoneNumber = re.sub('[\D]+', '', self.phoneNumberEdit.text()).lstrip('0')
        return countryCode, phoneNumber

    def _hasValidPhone(self):
        countryCode, phoneNumber = self._getPhone()
        return len(countryCode) > 0 and len(phoneNumber) > 0

    @Slot(str)
    def on_countryCodeEdit_textChanged(self, text):
        self._enableRegistration(self._hasValidPhone())

    @Slot(str)
    def on_phoneNumberEdit_textChanged(self, text):
        self._enableRegistration(self._hasValidPhone())

    def _enableRegistration(self, enabled):
        self.registrationGroup.setEnabled(enabled)
        self._passwordChanged()

    @Slot()
    def on_requestCallButton_clicked(self):
        self._requestRegistrationCode('voice', 'call')

    @Slot()
    def on_requestSMSButton_clicked(self):
        self._requestRegistrationCode('sms', 'SMS')

    def _isResponseOK(self, response, countryCode, phoneNumber):
        if response.get('status') == 'ok':
            return True
        message = 'Something went wrong. Are the country code and phone number correct?\n+%s %s\n\n' % (countryCode, phoneNumber)
        message += 'Server responded with:\n\n' + '\n'.join(['%s : %s' % (k, v) for k, v in response.items() if v is not None])
        print 'Registration Failed:\n', message
        QMessageBox.warning(self, 'Registration Failed', message)
        return False

    def _requestRegistrationCode(self, method, methodDescription):
        countryCode, phoneNumber = self._getPhone()
        req = WACodeRequestV2(countryCode, phoneNumber, Utilities.processIdentity(self._identity), method)
        response = req.send()
        if self._isResponseOK(response, countryCode, phoneNumber):
            if len(response.get('pw', '')) > 0:
                self._passwordReceived(response['pw'])
            else:
                message = 'You should receive a %s with your registration code soon.\n' % methodDescription
                message += 'Enter it in the registration dialog to register for your password.\n'
                QMessageBox.information(self, 'Registration Code Requested', message)

    @Slot(str)
    def on_registrationCodeEdit_textChanged(self, text):
        self.registerButton.setEnabled(len(self.registrationCodeEdit.text()) > 0)

    @Slot()
    def on_registerButton_clicked(self):
        code = self.registrationCodeEdit.text().replace(' ', '').replace('-', '')
        countryCode, phoneNumber = self._getPhone()
        req = WARegRequestV2(countryCode, phoneNumber, code, Utilities.processIdentity(self._identity))
        response = req.send()
        if self._isResponseOK(response, countryCode, phoneNumber):
            if len(response.get('pw', '')) > 0:
                self._passwordReceived(response['pw'])
            else:
                message = 'Something went wrong. Server sent OK, but no password:\n\n'
                message += '\n'.join(['%s : %s' % (k, v) for k, v in response.items() if v is not None])
                print 'Registration Failed:\n', message
                QMessageBox.warning(self, 'Registration Failed', message)

    def _passwordReceived(self, password):
        self.passwordEdit.setText(password)
        self._passwordChanged()
        message = 'Your new password has been received:\n%s\nIt will be saved in your config file.' % password
        QMessageBox.information(self, 'Password Received', message)
        self.on_okButton_clicked()

    @Slot(str)
    def on_passwordEdit_textChanged(self, text):
        self._checkPasswordEdit()

    def _checkPasswordEdit(self):
        hasPassword = len(self.passwordEdit.text()) > 0
        self.okButton.setEnabled(hasPassword)
        return hasPassword

    @Slot()
    def on_okButton_clicked(self):
        countryCode, phoneNumber = self._getPhone()
        password = self.passwordEdit.text()
        setConfig('countryCode', countryCode)
        setConfig('phoneNumber', phoneNumber)
        setConfig('password', password)
        self.accept()
