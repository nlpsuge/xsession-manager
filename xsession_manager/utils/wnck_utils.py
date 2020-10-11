# Note: Wnck may not works in Wayland

from time import time

import gi

gi.require_version('Wnck', '3.0')
from gi.repository import Wnck


def close_window_gracefully_async(window_id):
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    window: Wnck.Window = Wnck.Window.get(window_id)
    window.close(time())


def move_window_to(window_id, desktop_number):
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    ws = screen.get_workspace(desktop_number)
    if ws is None:
        print('Workspace(%d) not found!' % desktop_number)
    else:
        window: Wnck.Window = Wnck.Window.get(window_id)
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