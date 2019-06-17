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
from psycopg2 import Error

from .error_dialog import ErrorDialog

from PyQt5 import QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QLabel,
                             QSpacerItem,
                             QSizePolicy,
                             QHeaderView)

from qgis.core import QgsGeometry, QgsDataSourceUri, QgsProject
from qgis.gui import QgsRubberBand, QgsMapCanvas

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'event_dialog.ui'))

import re

# Convert a string representing a hstore from psycopg2 to a Python dict
kv_re = re.compile('"(\w+)"=>(NULL|""|".*?[^\\\\]")(?:, |$)')
def parse_hstore(hstore_str):
    if hstore_str is None:
        return {}
    return dict([(m.group(1), None if m.group(2) == 'NULL' else m.group(2).replace('\\"', '"')[1:-1]) for m in re.finditer(kv_re, hstore_str.decode('utf8'))])

def ewkb_to_geom(ewkb_str):
    if ewkb_str is None:
        return QgsGeometry()
    # get type + flags
    header = ewkb_str[2:10]
    has_srid = int(header[6], 16) & 2 > 0
    if has_srid:
        # remove srid flag
        header = header[:6] + "%X" % (int(header[6], 16) ^ 2) + header[7]
        # remove srid
        ewkb_str = ewkb_str[:2] + header + ewkb_str[18:]
    w = ewkb_str.decode('hex')
    g = QgsGeometry()
    g.fromWkb(w)
    return g

def reset_table_widget(table_widget):
    table_widget.clearContents()
    for r in range(table_widget.rowCount() - 1, -1, -1):
        table_widget.removeRow(r)

# Incremental loader
class EventModel(QAbstractTableModel):
    def __init__(self, cursor):
        QAbstractItemModel.__init__(self)
        self.cursor = cursor
        self.__data = []
        self.page_size = 100

    def flags(self, idx):
        return Qt.NoItemFlags | Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def data(self, idx, role = Qt.DisplayRole):
        #print idx.column(), role
        if idx.row() >= len(self.__data):
            rc = len(self.__data)
            # fetch more
            remaining = idx.row() - rc + 1
            for row in self.cursor.fetchmany(remaining):
                self.__data.append(row)

        row = self.__data[idx.row()]
        event_id, tstamp, table_name, action, application, row_data, changed_fields = row
        if idx.column() == 0:
            if role == Qt.DisplayRole:
                return tstamp.strftime("%x - %X")
            elif role == Qt.UserRole:
                return event_id
        elif idx.column() == 1:
            if role == Qt.DisplayRole:
                return table_name
        elif idx.column() == 2:
            if role == Qt.DisplayRole:
                if action == 'I':
                    return "Insertion"
                elif action == 'D':
                    return "Delete"
                elif action == 'U':
                    return "Update"
            elif role == Qt.UserRole:
                return action
        elif idx.column() == 3:
            if role == Qt.DisplayRole:
                return application
        return None

    def row_data(self, row):
        return parse_hstore(self.__data[row][5])

    def changed_fields(self, row):
        return parse_hstore(self.__data[row][6])

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return ("Date", "Table", "Action", "Application")[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def rowCount(self, parent):
        return self.cursor.rowcount

    def columnCount(self, parent):
        return 4

class GeometryDisplayer:

    def __init__(self, canvas ):
        self.canvas = canvas

        # main rubber
        self.rubber1 = QgsRubberBand(self.canvas)
        self.rubber1.setWidth(2)
        self.rubber1.setStrokeColor(self.newGeometryColor())
        self.rubber1.setFillColor(self.newGeometryColor())

        # old geometry rubber
        self.rubber2 = QgsRubberBand(self.canvas)
        self.rubber2.setWidth(2)
        self.rubber2.setStrokeColor(self.oldGeometryColor())
        self.rubber2.setFillColor(self.oldGeometryColor())

    def reset(self):
        self.rubber1.reset()
        self.rubber2.reset()

    def oldGeometryColor(self):
        return QColor("#ff5733")

    def newGeometryColor(self):
        return QColor("#00f")

    def display(self, geom1, geom2 = None):
        """
        @param geom1 base geometry (old geometry for an update)
        @param geom2 new geometry for an update
        """
        if geom2 is None:
            bbox = geom1.boundingBox()
            self.rubber1.setToGeometry(geom1, None)
        else:
            bbox = geom1.boundingBox()
            bbox.combineExtentWith(geom2.boundingBox())
            self.rubber1.setToGeometry(geom2, None)
            self.rubber2.setToGeometry(geom1, None)
        bbox.scale(1.5)
        self.canvas.setExtent(bbox)

class EventDialog(QDialog, FORM_CLASS):

    # Editable layer to alter edition mode (transaction group).
    editableLayerObject = None

    # Replay is not enabled.
    replayEnabled = False

    #
    # Internal.
    #
    catchLayerModifications = True

    def __init__(self, parent, connection_wrapper_read, connection_wrapper_write, map_canvas, audit_table, replay_function = None, table_map = {}, selected_layer_id = None, selected_feature_id = None):
        """Constructor.
        @param parent parent widget
        @param connection_wrapper_read connection wrapper (dbapi2)
        @param connection_wrapper_write connection wrapper (dbapi2 or transaction group)
        @param map_canvas the main QgsMapCanvas
        @param audit_table the name of the audit table in the database
        @param replay_function name of the replay function in the database
        @param table_map a dict that associates database table name to a QGIS layer id layer_id : table_name
        @param selected_layer_id selected layer
        @param selected_feature_id selected feature_id
        """
        super(EventDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # reload button icons
        self.searchButton.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons', 'mActionFilter2.svg')))
        self.replayButton.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons', 'mIconWarn.png')))

        # Store connections.
        self.connection_wrapper_read  = connection_wrapper_read
        self.connection_wrapper_write = connection_wrapper_write

        self.map_canvas = map_canvas
        self.audit_table = audit_table
        self.replay_function = replay_function

        # Watch for layer added or removed for replay button state update.
        QgsProject.instance().layersRemoved.connect(self.updateReplayButtonState)
        QgsProject.instance().layersAdded.connect(self.updateReplayButtonState)

        # Register all current layers.
        self.updateReplayButtonState()

        # geometry columns : table_name => list of geometry columns, the first one is the "main" geometry column
        self.geometry_columns = {}

        self.table_map = table_map

        # populate layer combo
        layer_idx = None
        for i, layer_id in enumerate(self.table_map.keys()):
            l = QgsProject.instance().mapLayer( layer_id )
            if l is None:
                continue
            print(layer_id, selected_layer_id)
            if layer_id == selected_layer_id:
                layer_idx = i + 1
            self.layerCombo.addItem(l.name(), layer_id)
        if layer_idx is not None:
            self.layerCombo.setCurrentIndex(layer_idx)

        if selected_feature_id is not None:
            self.idEdit.setEnabled(True)
            self.idEdit.setText(str(selected_feature_id))

        self.dataTable.hide()

        #
        # inner canvas
        self.vbox = QVBoxLayout()
        margins = self.vbox.contentsMargins()
        margins.setBottom(0)
        margins.setTop(11)
        margins.setLeft(0)
        margins.setRight(0)
        self.vbox.setContentsMargins(margins)
        self.inner_canvas = QgsMapCanvas()
        # copy layer set
        self.inner_canvas.setLayers([QgsMapLayer(l) for l in self.map_canvas.layers()])
        self.inner_canvas.setExtent(self.map_canvas.extent())
        self.geometryGroup.setLayout(self.vbox)
        self.geometryGroup.hide()

        self.hsplitter.setSizes([100,100])

        self.displayer = GeometryDisplayer(self.map_canvas)
        self.inner_displayer = GeometryDisplayer(self.inner_canvas)

        self.afterDt.setDateTime(QDateTime.currentDateTime())
        self.beforeDt.setDateTime(QDateTime.currentDateTime())

        self.advancedGroup.setCollapsed(True)

        # Old/new geometry legend.
        self.hbox = QHBoxLayout()

        self.oldGeometryLabel = QLabel()
        self.oldGeometryLabel.setText("------- old geometry")
        self.oldGeometryLabel.setStyleSheet("color: " + self.displayer.oldGeometryColor().name())

        self.newGeometryLabel = QLabel()
        self.newGeometryLabel.setText("------- new geometry (will be restored when replaying event)")
        self.newGeometryLabel.setStyleSheet("color: " + self.displayer.newGeometryColor().name())

        self.hbox.addWidget(self.oldGeometryLabel)
        self.hbox.addWidget(self.newGeometryLabel)
        self.hbox.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Fixed))

        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.inner_canvas)

        # refresh results when the search button is clicked
        self.searchButton.clicked.connect(self.populate)

        # update the feature id line edit visiblity based on the current layer selection
        self.layerCombo.currentIndexChanged.connect(self.onCurrentLayerChanged)

        # replay button
        if self.replay_function:
            self.replayButton.clicked.connect(self.onReplayEvent)

    def onCurrentLayerChanged(self, index):
        self.idEdit.setEnabled(index > 0)

    def done(self, status):
        self.undisplayGeometry()
        return QDialog.done(self, status)

    def populate(self):
        from qgis.core import QgsMessageLog
        wheres = []

        # filter by selected layer/table
        index = self.layerCombo.currentIndex()
        if index > 0:
            lid = self.layerCombo.itemData(index)
            schema, table = self.table_map[lid].split(".")
            wheres.append("schema_name = '{}'".format(schema))
            wheres.append("table_name = '{}'".format(table))

            # filter by feature id, if any
            if len(self.idEdit.text()) > 0:
                try:
                    id = int(self.idEdit.text())
                    wheres.append("row_data->'id'='{}'".format(id))
                except ValueError:
                    pass

        # filter by data
        if self.dataChck.isChecked():
            v = self.dataEdit.text()
            v = v.replace('\\', '\\\\').replace("'", "''").replace('%', '\\%').replace('_', '\\_')
            wheres.append("(SELECT string_agg(v,' ') FROM svals(row_data) as v) ILIKE '%{}%'".format(v))

        # filter by event type
        types = []
        if self.insertsChck.isChecked():
            types.append('I')
        if self.updatesChck.isChecked():
            types.append('U')
        if self.deletesChck.isChecked():
            types.append('D')
        wheres.append("action IN ('{}')".format("','".join(types)))

        # filter by dates
        if self.afterChck.isChecked():
            dt = self.afterDt.dateTime()
            wheres.append("action_tstamp_clk > '{}'".format(dt.toString(Qt.ISODate)))
        if self.beforeChck.isChecked():
            dt = self.beforeDt.dateTime()
            wheres.append("action_tstamp_clk < '{}'".format(dt.toString(Qt.ISODate)))

        # base query
        q = "SELECT event_id, action_tstamp_clk, schema_name || '.' || table_name, action, application_name, row_data, changed_fields FROM {} l".format(self.audit_table)
        # where clause
        if len(wheres) > 0:
            q += " WHERE " + " AND ".join(wheres)

        # Descending order.
        q += " ORDER BY action_tstamp_clk DESC"

        # Create cursor.
        cur = self.connection_wrapper_read.cursor()
        if cur == None:
            print("Cannot get cursor for database.")
            return

        cur.execute(q)

        self.eventModel = EventModel(cur)
        self.eventTable.setModel(self.eventModel)

        self.eventTable.selectionModel().currentRowChanged.connect(self.onEventSelection)

        self.eventTable.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)


    def updateReplayButton(self):
        self.replayButton.setEnabled(False)
        self.replayButton.setToolTip("No replay function or layer is in edition mode: replay action is not available.")

        if self.replay_function and self.replayEnabled == True:
            self.replayButton.setEnabled(True)
            self.replayButton.setToolTip("Replay the current selected item.")

    def onEventSelection(self, current_idx, previous_idx):
        reset_table_widget(self.dataTable)
        self.undisplayGeometry()

        # get current selection
        if current_idx.row() == -1:
            self.dataTable.hide()
            return
        i = current_idx.row()
        # action from current selection
        action = self.eventModel.data(self.eventModel.index(i, 2), Qt.UserRole)

        self.updateReplayButton()

        # get geometry columns
        data = self.eventModel.row_data(i)
        table_name = self.eventModel.data(self.eventModel.index(i, 1))
        gcolumns = self.geometry_columns.get(table_name)
        if gcolumns is None:
            schema, table = table_name.split('.')

            # Create cursor.
            cur = self.connection_wrapper_read.cursor()
            if cur == None:
                print("Cursor creation has failed")
                return

            q = "SELECT f_geometry_column FROM geometry_columns WHERE f_table_schema='{}' AND f_table_name='{}'".format(schema, table)
            cur.execute(q)
            self.geometry_columns[table_name] = [r[0] for r in cur.fetchall()]
            gcolumns = self.geometry_columns[table_name]

        # insertion or deletion
        if action == 'I' or action == 'D':
            self.dataTable.setColumnCount(2)
            self.dataTable.setHorizontalHeaderLabels(["Column", "Value"])
            j = 0
            for k, v in data.iteritems():
                if len(gcolumns) > 0 and k == gcolumns[0]:
                    self.displayGeometry(ewkb_to_geom(v))
                    continue
                if k in gcolumns:
                    continue
                if v is None:
                    continue
                self.dataTable.insertRow(j)
                self.dataTable.setItem(j, 0, QTableWidgetItem(k))
                self.dataTable.setItem(j, 1, QTableWidgetItem(v))
                j += 1
        # update
        elif action == 'U':
            self.dataTable.setColumnCount(3)
            self.dataTable.setHorizontalHeaderLabels(["Column", "Old value", "New value"])
            changed_fields = self.eventModel.changed_fields(i)
            j = 0
            for k, v in data.iteritems():
                if len(gcolumns) > 0 and k == gcolumns[0]:
                    w = changed_fields.get(k)
                    if w is not None:
                        self.displayGeometry(ewkb_to_geom(v), ewkb_to_geom(w))
                    continue
                if k in gcolumns:
                    continue
                w = changed_fields.get(k)
                if v is None and w is None:
                    continue
                self.dataTable.insertRow(j)
                self.dataTable.setItem(j, 0, QTableWidgetItem(k))
                self.dataTable.setItem(j, 1, QTableWidgetItem(v))
                if w is None:
                    self.dataTable.setItem(j, 2, QTableWidgetItem(v))
                else:
                    self.dataTable.setItem(j, 2, QTableWidgetItem(w))
                    if v != w:
                        b = QBrush(QColor("#ff8888"))
                        self.dataTable.item(j, 0).setBackground(b)
                        self.dataTable.item(j, 1).setBackground(b)
                        self.dataTable.item(j, 2).setBackground(b)
                j += 1
        self.dataTable.resizeColumnsToContents()
        #self.dataTable.sortByColumn(0, Qt.DescendingOrder)
        self.dataTable.show()

    def undisplayGeometry(self):
        self.geometryGroup.hide()
        self.displayer.reset()
        self.inner_displayer.reset()

    def displayGeometry(self, geom, geom2 = None):
        self.inner_displayer.display(geom, geom2)
        self.geometryGroup.show()

        if self.onMainCanvas.isChecked():
            self.displayer.display(geom, geom2)

    def onReplayEvent(self):
        i = self.eventTable.selectionModel().currentIndex().row()
        if i == -1:
            return
        # event_id from current selection
        event_id = self.eventModel.data(self.eventModel.index(i, 0), Qt.UserRole)

        error = ""

        q = "SELECT {}({})".format(self.replay_function, event_id)

        # Make a layer using transaction group editable to allow Sql execution.
        self.catchLayerModifications = False
        if self.editableLayerObject != None:
            self.editableLayerObject.startEditing()

        error = self.connection_wrapper_write.executeSql(q)

        if self.editableLayerObject != None:
            self.editableLayerObject.commitChanges()

        self.catchLayerModifications = True

        if error != "":
            self.error_dlg = ErrorDialog(self)
            self.error_dlg.setErrorText("An error has occurred during database access.")
            self.error_dlg.setContextText(error)
            self.error_dlg.setDetailsText("")
            self.error_dlg.exec_()

        self.connection_wrapper_write.commit()

        # refresh table
        self.populate()

        # Refresh replay button state.
        self.updateReplayButtonState()

    # Check if provided layer database connection is identical as current connection.
    def isLayerDatabaseCurrentConnection(self, layer):
        source = layer.source()

        layerUri  = QgsDataSourceUri(source)
        pluginuri = QgsDataSourceUri(self.connection_wrapper_read.db_source)

        return self.areConnectionsEquals(layerUri, pluginuri)

    # Compare connections.
    def areConnectionsEquals(self, connection1, connection2):

        # Service id defined: compare service & Ssl mode.
        service = connection1.service() + connection2.service()
        if service != "":
            if connection1.service() != connection2.service():
                return False

            if connection1.sslMode() != connection2.sslMode():
                return False

            # Connections are equals.
            return True

        # No service: compare host, port & database.
        if connection1.host() != connection2.host():
            return False

        if connection1.port() != connection2.port():
            return False

        if connection1.database() != connection2.database():
            return False

        # Connections are equals.
        return True

    # Reload replay button state by checking layer edition mode.
    def updateReplayButtonState(self, unused):
        self.updateReplayButtonState()

    def layerEditionModeChanged(self):
        self.updateReplayButtonState()

    def updateReplayButtonState(self):

        if self.catchLayerModifications == False:
            return

        self.editableLayerObject = None

        # Get all layers.
        layers = QgsProject.instance().mapLayers()

        self.replayEnabled = True

        for lid, layer in layers.items():

            # Check for layer using same database connection.
            usingSameDb = self.isLayerDatabaseCurrentConnection(layer)

            # Layer is in edition mode:
            if layer.isEditable() == True:

                # Check for database connection.
                if usingSameDb == True:
                    # Disable replay button.
                    self.replayEnabled = False

            # Layer is not editable: candidate for layer storage.
            # Store a layer that uses this connection.
            else:
                if usingSameDb == True:
                    self.editableLayerObject = layer

            # Watch layer edition mode changes.
            if getattr(layer, "beforeEditingStarted", None) != None and getattr(layer, "editingStopped", None) != None:
                try:
                    layer.editingStarted.connect(self.layerEditionModeChanged, Qt.UniqueConnection)
                    layer.editingStopped.connect(self.layerEditionModeChanged, Qt.UniqueConnection)
                except:
                    pass

        self.updateReplayButton()
