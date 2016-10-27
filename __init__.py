def name():
    return u"PostgreSQL history viewer"
def description():
    return u"History viewer for a PostgreSQL base with audit triggers"
def version():
    return u"0.1"
def qgisMinimumVersion():
    return u"2.0"
def qgisMaximumVersion():
    return u"9.99"
def classFactory(iface):
    from main import Plugin
    return Plugin(iface)
