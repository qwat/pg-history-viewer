def name():
    return u"PostgreSQL history viewer"


def description():
    return u"History viewer for a PostgreSQL base with audit triggers"


def version():
    return u"1.0"


def qgisMinimumVersion():
    return u"3.4"


def qgisMaximumVersion():
    return u"9.99"


def classFactory(iface):
    from .main import Plugin
    return Plugin(iface)
