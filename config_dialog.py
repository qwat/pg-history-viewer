# -*- coding: utf-8 -*-
import os

from PyQt4 import uic
from PyQt4.QtCore import QSettings, QPoint
from PyQt4.QtGui import QDialog, QMessageBox, QMenu, QIcon

from qgis.core import QgsProject, QgsLayerTreeModel
from qgis.gui import QgsLayerTreeView

import psycopg2

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'config.ui'))

class ConfigDialog(QDialog, FORM_CLASS):
    def __init__(self, parent, db_connection = "", audit_table = "", table_map = {}, replay_function = None):
        """Constructor.
        @param parent parent widget
        """
        super(ConfigDialog, self).__init__(parent)
        self.setupUi(self)

        self.reloadBtn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons', 'repeat.svg')))

        self._table_map = table_map

        self.tree_group = QgsProject.instance().layerTreeRoot().clone()
        self.tree_model = QgsLayerTreeModel(self.tree_group)
        self.treeView.setModel(self.tree_model)

        self.treeView.currentLayerChanged.connect(self.onLayerChanged)

        self.reloadBtn.clicked.connect(self.onDatabaseChanged)
        self.dbConnectionBtn.clicked.connect(self.onBrowseConnection)
        self.tableCombo.currentIndexChanged.connect(self.onTableEdit)

        if db_connection:
            self.dbConnectionText.setText(db_connection)
            self.reloadBtn.click()
            if audit_table:
                self.auditTableCombo.setCurrentIndex(self.auditTableCombo.findText(audit_table))
            if replay_function:
                self.replayFunctionCombo.setCurrentIndex(self.replayFunctionCombo.findText(replay_function))
                self.replayFunctionChk.setChecked(True)

        self.conn = None
        self.tables = None

    def onBrowseConnection(self):
        s = QSettings()
        base = "/PostgreSQL/connections"
        s.beginGroup("/PostgreSQL/connections")
        children = s.childGroups()
        connections = {}
        map = {"dbname":"database", "host":"host", "port":"port", "service":"service", "password":"password", "user":"username"}
        for g in children:
            s.beginGroup(g)
            cstring = ""
            for k, v in map.items():
                if s.value(v):
                    cstring += k + "=" + s.value(v) + " "
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
        try:
            self.conn = psycopg2.connect(dbparams)
        except psycopg2.OperationalError as e:
            QMessageBox.critical(None, "PostgreSQL connection problem", e.message)
            return

        cur = self.conn.cursor()
        # populate tables
        q = "SELECT table_schema ,table_name FROM information_schema.tables" \
            " where table_schema not in ('pg_catalog', 'information_schema') order by table_schema, table_name"
        cur.execute(q)
        self.auditTableCombo.clear()
        self.tableCombo.clear()
        self.tableCombo.addItem("")
        for r in cur.fetchall():
            t = r[0] + "." + r[1]
            self.auditTableCombo.addItem(t)
            self.tableCombo.addItem(t)

        # populate functions
        q = "select routine_schema, routine_name from information_schema.routines where " \
            "routine_schema not in ('pg_catalog', 'information_schema') " \
            "and data_type = 'void' " \
            "and substr(routine_name, 1, 1) != '_'"
        cur.execute(q)
        self.replayFunctionCombo.clear()
        for r in cur.fetchall():
            t = r[0] + "." + r[1]
            self.replayFunctionCombo.addItem(t)

    def onLayerChanged(self, layer):
        if layer is None:
            return
        table_name = self._table_map.get(layer.id())
        if table_name is not None:
            idx = self.tableCombo.findText(table_name)
            self.tableCombo.setCurrentIndex(idx)
        else:
            self.tableCombo.setCurrentIndex(0)

    def onTableEdit(self, idx):
        table_name = self.tableCombo.itemText(idx)
        current = self.treeView.currentLayer()
        if current is not None:
            self._table_map[current.id()] = table_name

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

        
        
