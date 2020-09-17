# pg-history-viewer
QGIS plugin that helps to visualize contents of a PostgreSQL [audit trigger table](https://wiki.postgresql.org/wiki/Audit_trigger).

This is inspired by [the Postgres 91 plus Auditor](https://github.com/3nids/postgres91plusauditor) QGIS plugin.

The main features are:
- visualization of contents of the audit table
- advanced search on the table by means of a SQL query
  - search by type of events (insert, delete, update)
  - search by date
  - free text search in the data
- support geometry display
- replay of an event
- support huge audit table by incremental loading

![Screenshot](screenshot.png)

# INSTALL

## audit trigger functions

Audit trigger functions are well described here [audit trigger table](https://wiki.postgresql.org/wiki/Audit_trigger).
On the behalf of QWAT's group, new features were added to audit views and replay edits. They are available here:
https://gitlab.com/Oslandia/audit_trigger. We had to fork unmaintained 2nd Quandrant's source repository https://github.com/2ndQuadrant/audit-trigger. If somehow this repository is revived, please tell us and we'll switch back to it. 

To install the trigger functions, download the audit.sql file from there, and execute the sql commands in the script, either from pgadmin or PostgreSQL.

To start logging a table, here 'qwat_dr.annotationline':

`audit.audit_table('qwat_dr.annotationline');`

or for a view; here 'qwat_od.vw_consumptionzone':

`audit.audit_view('qwat_od.vw_consumptionzone', 'true'::boolean, '{}'::text[], '{id}'::text[]);`



## QGIS plugin

QGIS plugin can be installed from the QGIS plugin installer or by downloading this source code and unzipping it to your QGIS plugin profile or additional plugin paths. See https://docs.qgis.org/3.10/en/docs/user_manual/plugins/plugins.html
