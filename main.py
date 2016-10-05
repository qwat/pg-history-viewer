import os

# import from __init__
from . import name as plugin_name

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import QAction, QIcon, QMessageBox

from qgis.core import QgsMapLayerRegistry, QgsProject

import psycopg2

import event_dialog
import config_dialog

PLUGIN_PATH=os.path.dirname(__file__)

def database_connection_string():
    db_connection, ok = QgsProject.instance().readEntry("HistoryViewer", "db_connection", "")
    return db_connection

def set_database_connection_string(db_connection):
    QgsProject.instance().writeEntry("HistoryViewer", "db_connection", db_connection)

def project_audit_table():
    audit_table, ok = QgsProject.instance().readEntry("HistoryViewer", "audit_table", "")
    return audit_table

def set_project_audit_table(audit_table):
    QgsProject.instance().writeEntry("HistoryViewer", "audit_table", audit_table)

def project_table_map():
    # get table_map
    table_map_strs, ok = QgsProject.instance().readListEntry("HistoryViewer", "table_map", [])
    # list of "layer_id=table_name" strings
    table_map = dict([t.split('=') for t in table_map_strs])
    return table_map

def set_project_table_map(table_map):
    QgsProject.instance().writeEntry("HistoryViewer", "table_map", [k+"="+v for k,v in table_map.items()])


class Plugin():
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.listEventsAction = QAction(QIcon(os.path.join(PLUGIN_PATH, "icons", "qaudit-64.png")), u"List events", self.iface.mainWindow())
        self.listEventsAction.triggered.connect(self.onListEvents)

        self.iface.addToolBarIcon(self.listEventsAction)
        self.iface.addPluginToMenu(plugin_name(), self.listEventsAction)

        self.configureAction = QAction(u"Configuration", self.iface.mainWindow())
        self.configureAction.triggered.connect(self.onConfigure)
        self.iface.addPluginToMenu(plugin_name(), self.configureAction)


    def unload(self):
        self.iface.removeToolBarIcon(self.listEventsAction)
        self.iface.removePluginMenu(plugin_name(),self.listEventsAction)
        self.iface.removePluginMenu(plugin_name(),self.configureAction)

    def onListEvents(self, layer_id = None, feature_id = None):
        db_connection = database_connection_string()
        if not db_connection:
            QMessageBox.critical(None, "Configuration problem", "No database configuration has been found, please configure the project")
            self.onConfigure()
            return

        conn = psycopg2.connect(db_connection)

        table_map = project_table_map()
        
        self.dlg = event_dialog.EventDialog(self.iface.mainWindow(),
                                            conn,
                                            self.iface.mapCanvas(),
                                            table_map = table_map,
                                            selected_layer_id = layer_id,
                                            selected_feature_id = feature_id)
        self.dlg.show()

    def onConfigure(self):
        table_map = project_table_map()
        db_connection = database_connection_string()
        audit_table = project_audit_table()
        self.config_dlg = config_dialog.ConfigDialog(self.iface.mainWindow(), db_connection, audit_table, table_map)
        r = self.config_dlg.exec_()
        if r == 1:
            table_map = self.config_dlg.table_map()
            db_connection = self.config_dlg.db_connection()
            audit_table = self.config_dlg.audit_table()
            # save to the project
            set_database_connection_string(db_connection)
            set_project_table_map(table_map)
            set_project_audit_table(audit_table)

