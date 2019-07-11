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
    os.path.dirname(__file__), 'error_dialog.ui'))

class ErrorDialog(QDialog, FORM_CLASS):
    def __init__(self, parent):
        super(ErrorDialog, self).__init__(parent)
        self.setupUi(self)

        self.closeButton.clicked.connect(self.deleteLater)

    def setErrorText(self, text):
        self.errorText.setText(text)

    def setDetailsText(self, text):
        self.detailsText.setText(text)

    def setContextText(self, text):
        self.contextText.setPlainText(text)
