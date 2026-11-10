def name():
    return "PostgreSQL history viewer"


def classFactory(iface):
    from .main import Plugin

    return Plugin(iface)
