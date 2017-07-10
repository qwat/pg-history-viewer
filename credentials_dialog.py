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

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'credentials_dialog.ui'))

class CredentialsDialog(QDialog, FORM_CLASS):
    
    saveCredentialsRequested = pyqtSignal('QString', 'QString', name='saveCredentialsRequested')
    retryRequested = pyqtSignal(name='retryRequested')
    
    def __init__(self, parent):
        super(CredentialsDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.retryButton.clicked.connect(self.onValidation)
        self.cancelButton.clicked.connect(self.deleteLater)
        
    def setErrorText(self, text):
        self.errorText.setText(text)
    
    def setDomainText(self, text):
        self.domainText.setText(text)
        
    def setUserText(self, text):
        self.userText.setText(text)
        
    def setPasswordText(self, text):
        self.passwordText.setText(text)
        
    def onValidation(self):
        # Emit informations.
        self.saveCredentialsRequested.emit(self.userText.text(), self.passwordText.text())
        self.retryRequested.emit()

        self.deleteLater()
