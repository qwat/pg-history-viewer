"""
/**
 *   Copyright (C) 2017 Oslandia <infos@oslandia.com>
 *
 *   This library is free software; you can redistribute it and/or
 *   modify it under the terms of the GNU Library General Public
 *   License as published by the Free Software Foundation; either
 *   version 2 of the License, or (at your option) any later version.
 *
 *   This library is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *   Library General Public License for more details.
 *   You should have received a copy of the GNU Library General Public
 *   License along with this library; if not, see <http://www.gnu.org/licenses/>.
 */
"""
# -*- coding: utf-8 -*-
import os

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'credentials_dialog.ui'))

# Display a dialog for user credentials input.


class CredentialsDialog(QDialog, FORM_CLASS):
    def setErrorText(self, text):
        self.errorText.setText(text)

    def setDomainText(self, text):
        self.domainText.setText(text)

    def setUserText(self, text):
        self.userText.setText(text)

    def setPasswordText(self, text):
        self.passwordText.setText(text)

    def getUserText(self):
        return self.userText.text()

    def getPasswordText(self):
        return self.passwordText.text()

    def hasUserCanceled(self):
        return self.userHasCancel

    #
    # Internal members.
    #
    userHasCancel = False

    def __init__(self, parent):
        super(CredentialsDialog, self).__init__(parent)
        self.setupUi(self)

        self.retryButton.clicked.connect(self.onValidation)
        self.cancelButton.clicked.connect(self.onCancel)

    def onValidation(self):
        self.close()
        self.userHasCancel = False

    def onCancel(self):
        self.userHasCancel = True

        self.close()

    def closeEvent(self, event):
        self.userHasCancel = True

    def keyPressEvent(self, event):
        if not event.key() == Qt.Key_Escape:
            super(QDialog, self).keyPressEvent(event)

        else:
            self.onCancel()
