# https://developer.gnome.org/glib/stable/glib-The-Main-Event-Loop.html
# https://developer.gnome.org/libwnck/stable/getting-started.html

import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
from gi.repository import GLib


class MainLoop:

    def __init__(self):
        Gdk.init([])
        self.loop = GLib.MainLoop.new(None, False)

    def get_loop(self):
        return self.loop

    def run(self):
        self.loop.run()
        self.loop.unref()

    def quit(self):
        self.loop.quit()
