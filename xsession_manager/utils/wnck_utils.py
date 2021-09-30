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
        if window:
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
    # Fix: gnome-extensions has empty value of window.get_class_group_name()
    if name == '' or name is None:
        return window.get_application().get_name()
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
    window: Wnck.Window = get_window(xid)
    if not window:
        return False
    return window.is_sticky()


def stick(xid: int, if_not_sticky: bool=True):
    window: Wnck.Window = get_window(xid)
    if if_not_sticky and window:
        _is_sticky = window.is_sticky()
        if not _is_sticky:
            window.stick()
    else:
        if window:
            window.stick()


def is_above(xid: int) -> bool:
    window: Wnck.Window = get_window(xid)
    return window.is_above()


def make_above(xid: int):
    window: Wnck.Window = get_window(xid)
    window.make_above()


def count_windows(xid: int) -> int:
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    window: Wnck.Window = Wnck.Window.get(xid)
    # Windows may not open yet
    if window is None:
        return -1

    app: Wnck.Application = window.get_application()
    return app.get_n_windows()


def get_geometry(xid: int) -> (int, int, int, int):
    window = get_window(xid)
    if window:
        geometry = window.get_geometry()
        xp = geometry.xp
        yp = geometry.yp
        widthp = geometry.widthp
        heightp = geometry.heightp
        return xp, yp, widthp, heightp

    return None


def set_geometry(xid: int, xp: int, yp: int, widthp: int, heightp: int):
    window = get_window(xid)
    if window:
        _if_set_geometry = True

        geometry = get_geometry(xid)
        if geometry:
            x_offset, y_offset, width, height = geometry
            if xp == x_offset and yp == y_offset and width == widthp and height == heightp:
                _if_set_geometry = False

        if _if_set_geometry is False:
            return

        geometry_mask: Wnck.WindowMoveResizeMask = (
                Wnck.WindowMoveResizeMask.X |
                Wnck.WindowMoveResizeMask.Y |
                Wnck.WindowMoveResizeMask.WIDTH |
                Wnck.WindowMoveResizeMask.HEIGHT)
        window.set_geometry(Wnck.WindowGravity.CURRENT, geometry_mask, xp, yp, widthp, heightp)
