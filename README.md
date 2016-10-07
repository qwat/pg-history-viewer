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
