# Note: Wnck may not works in Wayland

from time import time

import gi

gi.require_version('Wnck', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Wnck, Gtk


def close_window_gracefully_async(window_id: int):
    window: Wnck.Window = get_window(window_id)
    # window may be None if this window has been closed by the user
    if window:
        window.close(time())


def move_window_to(window_id, desktop_number):
    screen: Wnck.Screen = Wnck.Screen.get_default()
    # In case that cannot get the Wnck.Workspace instance
    while Gtk.events_pending():
        Gtk.main_iteration()
    screen.force_update()
    ws = screen.get_workspace(desktop_number)
    if ws is None:
        print('Workspace %d not found!' % desktop_number)
    else:
        window: Wnck.Window = get_window(window_id)
        window.move_to_workspace(ws)


def is_gnome() -> bool:
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    wmn = screen.get_window_manager_name()
    if wmn == 'GNOME Shell':
        return True
    return False


def get_workspace_count():
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    return screen.get_workspace_count()


def get_app_name(xid: int) -> str:
    window = get_window(xid)
    # See: https://developer.gnome.org/libwnck/stable/WnckWindow.html#wnck-window-get-class-group-name
    # See: https://tronche.com/gui/x/icccm/sec-4.html#WM_CLASS
    name = window.get_class_group_name()
    if name == 'Wine':  # eg: https://snapcraft.io/notepad-plus-plus
        # Return a reasonable name
        return window.get_class_instance_name()
    return name


def get_window(xid: int) -> Wnck.Window:
    screen: Wnck.Screen = Wnck.Screen.get_default()
    # In case that cannot get the window according to xid
    while Gtk.events_pending():
        Gtk.main_iteration()
    screen.force_update()
    window: Wnck.Window = Wnck.Window.get(xid)
    return window


def get_window_title(xid: int) -> str:
    window = get_window(xid)
    return window.get_name()


def is_sticky(xid: int) -> bool:
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    window: Wnck.Window = Wnck.Window.get(xid)
    return window.is_sticky()


def count_windows(xid: int) -> int:
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    window: Wnck.Window = Wnck.Window.get(xid)
    # Windows may not open yet
    if window is None:
        return -1

    app: Wnck.Application = window.get_application()
    return app.get_n_windows()
