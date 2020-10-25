from typing import List, Dict

import gi
import psutil

from utils import snapd_workaround

gi.require_version('Wnck', '3.0')
from gi.repository import Wnck


def get_all_snap_processes() -> List[str]:
    print()
    screen: Wnck.Screen = Wnck.Screen.get_default()
    screen.force_update()
    windows: List[Wnck.Window] = screen.get_windows()
    snap_processes = []
    for w in windows:
        pid = w.get_pid()
        p = psutil.Process(pid)
        cmdline = p.cmdline()

        for cl in cmdline:
            if 'snap' in cl:
                snap_processes.append(cl)

    return snap_processes


def test_is_snap():
    all_snap_processes = get_all_snap_processes()
    for sc in all_snap_processes:
        assert snapd_workaround.Snapd().is_snap_app(sc)


def test_get_desktop_file():
    snapd = snapd_workaround.Snapd()
    all_apps: List[Dict] = snapd.get_app('opera')
    for aa in all_apps:
        if 'desktop-file' in aa:
            desktop_file: str = aa['desktop-file']
            assert desktop_file.endswith('.desktop')


def test_launch_app():
    launched = snapd_workaround.Snapd().launch(['authy'], False, False)
    assert launched is True

