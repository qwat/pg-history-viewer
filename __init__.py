def name():
    return "PostgreSQL history viewer"


def description():
    return "History viewer for a PostgreSQL base with audit triggers"


def version():
    return "1.0"


def qgisMinimumVersion():
    return "3.4"


def qgisMaximumVersion():
    return "9.99"


def classFactory(iface):
    from .main import Plugin

    return Plugin(iface)
