import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Wnck
from gi.repository import Gdk


class GdkUtils:

    def __init__(self):
        pass

    def get_monitor_count(self):
        gdk_display = Gdk.Display.get_default()
        monitor_count = gdk_display.get_n_monitors()
        return monitor_count


