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

# import from __init__
from . import name as plugin_name

from PyQt4.QtCore import QSettings
from PyQt4.QtGui import QAction, QIcon, QMessageBox

from qgis.core import QgsMapLayerRegistry, QgsProject, QgsDataSourceURI

from psycopg2 import Error

import psycopg2

import event_dialog
import config_dialog
import credentials_dialog
import connection_wrapper

PLUGIN_PATH=os.path.dirname(__file__)

def database_connection_string():
    db_connection, ok = QgsProject.instance().readEntry("HistoryViewer", "db_connection", "")
    return db_connection

def set_database_connection_string(db_connection):
    QgsProject.instance().writeEntry("HistoryViewer", "db_connection", db_connection)

def project_audit_table():
    audit_table, ok = QgsProject.instance().readEntry("HistoryViewer", "audit_table", "")
    return audit_table

def set_project_replay_function(replay_function):
    QgsProject.instance().writeEntry("HistoryViewer", "replay_function", replay_function)

def project_replay_function():
    replay_function, ok = QgsProject.instance().readEntry("HistoryViewer", "replay_function", "")
    return replay_function

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
        
        # Create database connection wrappers.
        self.connection_wrapper_read = connection_wrapper.ConnectionWrapper()
        self.connection_wrapper_read.disableTransactionGroup(True)
        
        self.connection_wrapper_write = connection_wrapper.ConnectionWrapper()

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
        # Get database connection string.
        db_connection = database_connection_string()
        if not db_connection:
            QMessageBox.critical(None, "Configuration problem", "No database configuration has been found, please configure the project")
            r = self.onConfigure()
            
            # Retry if needed.
            if r == 1:
                self.onListEvents(layer_id, feature_id)
            
            return
            
        # Create database connections.
        self.connection_wrapper_read.openConnection(db_connection)
        
        # Reuse read connection for write direct connection.
        self.connection_wrapper_write.psycopg2Connection = self.connection_wrapper_read.psycopg2Connection
        self.connection_wrapper_write.openConnection(db_connection)

        # Database connection has failed.
        if self.connection_wrapper_read.isValid() == False or self.connection_wrapper_write.isValid() == False:
            print "No database connection established."
            return

        # Database connection success.
        table_map = project_table_map()
        
        self.dlg = event_dialog.EventDialog(self.iface.mainWindow(),
                                            self.connection_wrapper_read,
                                            self.connection_wrapper_write,
                                            self.iface.mapCanvas(),
                                            project_audit_table(),
                                            replay_function = project_replay_function(),
                                            table_map = table_map,
                                            selected_layer_id = layer_id,
                                            selected_feature_id = feature_id)
                                            
        # Populate dialog & catch error if any.
        try:
            self.dlg.populate()
            
        except Error as e:
            QMessageBox.critical(None, "Configuration problem", "Database configuration is invalid, please check the project configuration")
            r = self.onConfigure()
            
            # Retry if needed.
            if r == 1:
                self.onListEvents(layer_id, feature_id)
            
            return
        
        self.dlg.show()

    def onConfigure(self):
        table_map = project_table_map()
        db_connection = database_connection_string()
        audit_table = project_audit_table()
        replay_function = project_replay_function()
        self.config_dlg = config_dialog.ConfigDialog(self.iface.mainWindow(), db_connection, audit_table, table_map, replay_function)
        r = self.config_dlg.exec_()
        
        if r == 1:
            # save to the project
            set_database_connection_string(self.config_dlg.db_connection())
            set_project_table_map(self.config_dlg.table_map())
            set_project_audit_table(self.config_dlg.audit_table())
            set_project_replay_function(self.config_dlg.replay_function())
            
        return r
