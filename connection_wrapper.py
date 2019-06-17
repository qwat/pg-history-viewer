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
from qgis.core import QgsTransactionGroup, QgsProject, QgsDataSourceUri
from psycopg2 import Error

from .credentials_dialog import CredentialsDialog
import psycopg2
import os

# This object contains database connection wrapped for both
# psycopg2 direct database connection OR QGis transaction group
# connection.
#
# First open database connection: openConnection().
# In second time, use executeSql() and commit().
# In last time delete connection: closeConnection().
#
# In some case transaction group cannot be used. To disable transaction
# group use disableTransactionGroup().
# Direct connection allow the use of cursor() for cursor creation.
class ConnectionWrapper():

    # Disable transaction group.
    def disableTransactionGroup(self, disabled):
        self.qgisTransactionGroupDisabled = disabled

    # Create database connection.
    # db_connection: database connection string.
    def openConnection(self, db_connection):
        # Check for connection is already open.
        if self.isConnected() and self.db_source == db_connection:
            print("Connection already open: reusing it.")
            return

        self.db_source = db_connection

        self.closeConnection()

        # Try to retrieve transaction group if enabled.
        if self.qgisTransactionGroupDisabled == False:
            tgConn = self.createConnectionFromTransactionsGroup(db_connection)

            if tgConn != None:
                self.storeQGisTransactionGroupConnection(tgConn)
                return

        # Transaction group not available: try to create direct connection.
        if self.psycopg2Connection == None:
            dirConn = self.createSingleConnection(db_connection)

            if dirConn != None:
                self.storePsycopg2Connection(dirConn)

    # Check for a valid connection has been wrapped.
    def isValid(self):
        if self.psycopg2Connection == None and self.qgisTransactionGroupConnection == None:
            return False

        return True

    # Execute Sql on database connection if available.
    # Prior to transaction group.
    def executeSql(self, sql):

        # Use QGis.QgsTransactionGroup connection.
        if self.qgisTransactionGroupConnection != None:
            error = self.qgisTransactionGroupConnection.executeSql(sql)

            # HACK: PostgreSql can return "Status 2 ()" when PGRES_TUPLES_OK is returned.
            if error == "Status 2 ()":
                return ""

            if error != "":
                return error

        # Use psycopg2 connection.
        elif self.psycopg2Connection != None:
            cursor = self.psycopg2Connection.cursor()

            if cursor == None:
                return "Invalid database connection: cannot get cursor."

            try:
                cursor.execute(sql)

            except Exception as ex:
                return ex.diag.context

            return ""

        return "No connection to database. Please connect before."

    # Commit Sql on database.
    def commit(self):

        # Use psycopg2 connection.
        if self.psycopg2Connection != None:
            self.psycopg2Connection.commit()

        # Use QGis.QgsTransactionGroup connection.
        elif self.qgisTransactionGroupConnection != None:
            # No commit for transaction group.
            pass

        else:
            print("Connection wrapper doesn't store any database connection!")

    # Create new cursor. For direct connection only.
    def cursor(self):
        if self.psycopg2Connection != None:
            return self.psycopg2Connection.cursor()

        print("Cannot create cursor without direct connection!")

        return None

    # Close connection.
    def closeConnection(self):

        if self.psycopg2Connection != None:
            del self.psycopg2Connection
            self.psycopg2Connection = None

        if self.qgisTransactionGroupConnection != None:
            del self.qgisTransactionGroupConnection
            self.qgisTransactionGroupConnection = None

    # Check for open connection available.
    def isConnected(self):
        if self.psycopg2Connection != None:
            return True

        if self.qgisTransactionGroupConnection != None:
            return True

        return False

    #
    # Internal members.
    #
    db_source = ""

    # psycopg2 database connection.
    psycopg2Connection = None

    # QGis.QgsTransactionGroup database connection.
    qgisTransactionGroupConnection = None
    qgisTransactionGroupDisabled   = False

    def __exit__(self, exc_type, exc_value, traceback):
        self.closeConnection()

    def storePsycopg2Connection(self, connection):
        self.psycopg2Connection = connection

    def storeQGisTransactionGroupConnection(self, connection):
        self.qgisTransactionGroupConnection = connection

    # Create database connection from existing transactions group.
    def createConnectionFromTransactionsGroup(self, db_connection):
        # Check for QGis project permits to use transactions group.
        activated = False

        try:
            activated = QgsProject.instance().autoTransaction()

        except:
            print("QGis project doesn't provide QgsProject::autoTransaction() method.")
            return None

        if not activated:
            print("This QGis project has disabled transactions group.")
            return None

        # Get transactions group.

        # Pg plugin allows only 'postgres' provider.
        providerKey = "postgres"

        # Database string. Removing user.
        sourceUri = QgsDataSourceUri(db_connection)
        sourceUri.setUsername("")

        uriStr = sourceUri.connectionInfo()

        try:
            print("Getting transactions group for provider ", providerKey, " and database connection: ", uriStr)
            return QgsProject.instance().transactionGroup(providerKey, uriStr)

        except:
            print("QgsProject::transactionGroup(): unavailable feature.")
            return None

        return None

    # Create database connection with psycopg2.
    def createSingleConnection(self, db_connection):
        # Create new single connection.
        conn = None

        try:
            conn = psycopg2.connect(db_connection)

        except Exception as ex:
            # Ask user for credentials.
            self.credDlg = CredentialsDialog(None)

            self.credDlg.setErrorText(str(ex))
            self.credDlg.setDomainText(db_connection)
            self.credDlg.setPasswordText("")

            self.credDlg.exec_()

            # User has canceled: abort.
            if self.credDlg.hasUserCanceled():
                return None

            # User has validated: get credentials & create single connection again.
            else:
                db_connection = db_connection + "user='" + self.credDlg.getUserText() + "' password='" + self.credDlg.getPasswordText() + "'"

                return self.createSingleConnection(db_connection)

        # Create has been successfull done.
        return conn
