"""
/**
 *   Copyright (C) 2016 Oslandia <infos@oslandia.com>
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
from PyQt4.QtCore import QSettings, QPoint
from PyQt4.QtGui import QDialog, QMessageBox, QMenu, QIcon

from qgis.core import QgsProject, QgsLayerTreeModel, QgsDataSourceURI
from qgis.gui import QgsLayerTreeView

import connection_wrapper

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'config.ui'))

class ConfigDialog(QDialog, FORM_CLASS):
    def __init__(self, parent, db_connection = "", audit_table = "", table_map = {}, replay_function = None):
        """Constructor.
        @param parent parent widget
        """
        super(ConfigDialog, self).__init__(parent)
        self.setupUi(self)

        self.reloadBtn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons', 'repeat.svg')))

        self._table_map = table_map
        
        # Create database connection wrapper.
        # Disabled transaction group.
        self.connection_wrapper = connection_wrapper.ConnectionWrapper()
        self.connection_wrapper.disableTransactionGroup(True)

        self.reloadBtn.clicked.connect(self.onDatabaseChanged)
        self.dbConnectionBtn.clicked.connect(self.onBrowseConnection)

        if db_connection:
            self.dbConnectionText.setText(db_connection)
            self.reloadBtn.click()
            if audit_table:
                self.auditTableCombo.setCurrentIndex(self.auditTableCombo.findText(audit_table))
            if replay_function:
                self.replayFunctionCombo.setCurrentIndex(self.replayFunctionCombo.findText(replay_function))
                self.replayFunctionChk.setChecked(True)

        self.tables = None
        
    def sslModeToString(self, mode):
        sslMode = QgsDataSourceURI.SSLmode(mode)
        
        if sslMode == int(QgsDataSourceURI.SSLdisable):
            return "disable"
        if sslMode == int(QgsDataSourceURI.SSLallow):
            return "allow"
        if sslMode == int(QgsDataSourceURI.SSLrequire):
            return "require"
        if sslMode == int(QgsDataSourceURI.SSLverifyCA):
            return "verify-ca"
        if sslMode == int(QgsDataSourceURI.SSLverifyFull):
            return "verify-full"
        
        # Default empty value: SSLprefer.
        return ""

    def onBrowseConnection(self):
        s = QSettings()
        base = "/PostgreSQL/connections"
        s.beginGroup("/PostgreSQL/connections")
        children = s.childGroups()
        connections = {}
        map = {"dbname":"database", "host":"host", "port":"port", "service":"service", "password":"password", "user":"username", "sslmode": "sslmode"}
        for g in children:
            s.beginGroup(g)
            cstring = ""
            for k, v in map.items():
                # Strings attributes.
                if s.value(v) and k != "sslmode":
                    cstring += k + "=" + s.value(v) + " "
                
                # Enum attributes (Ssl mode).
                elif s.value(v) and k == "sslmode":
                    mode = self.sslModeToString(s.value(v))
                    if mode != "":
                        cstring += k + "=" + mode + " "
                    
            connections[g] = cstring
            s.endGroup()

        menu = QMenu(self)
        for k in sorted(connections.keys()):
            menu.addAction(k)

        def onMenu(action):
            self.dbConnectionText.setText(connections[action.text()])
            self.reloadBtn.click()

        menu.triggered.connect(onMenu)
        menu.exec_(self.dbConnectionBtn.mapToGlobal(QPoint(0,0)))

    def onDatabaseChanged(self):
        dbparams = self.dbConnectionText.text()
        
        # Clear ui.
        self.auditTableCombo.clear()
        self.replayFunctionCombo.clear()
        
        # Connect to database.
        self.connection_wrapper.openConnection(dbparams)
        if self.connection_wrapper.isValid() == False:
            return

        # Create cursor.
        cur = self.connection_wrapper.cursor()
        if cur == None:
            return
        
        # populate tables
        q = "SELECT table_schema ,table_name FROM information_schema.tables" \
            " where table_schema not in ('pg_catalog', 'information_schema') order by table_schema, table_name"
            
        cur.execute(q)
        
        for r in cur.fetchall():
            t = r[0] + "." + r[1]
            self.auditTableCombo.addItem(t)

        # populate functions
        q = "select routine_schema, routine_name from information_schema.routines where " \
            "routine_schema not in ('pg_catalog', 'information_schema') " \
            "and data_type = 'void' " \
            "and substr(routine_name, 1, 1) != '_'"
            
        cur.execute(q)
        
        for r in cur.fetchall():
            t = r[0] + "." + r[1]
            self.replayFunctionCombo.addItem(t)

    def table_map(self):
        return self._table_map

    def audit_table(self):
        return self.auditTableCombo.currentText()

    def replay_function(self):
        if not self.replayFunctionChk.isChecked():
            return None
        return self.replayFunctionCombo.currentText()

    def db_connection(self):
        return self.dbConnectionText.text()
