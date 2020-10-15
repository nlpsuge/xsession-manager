# See also: https://linux.die.net/man/1/wmctrl


import subprocess


def get_running_windows_raw() -> list:
    output = subprocess.check_output('wmctrl -lpG', shell=True)
    lines = output.splitlines()
    return [line.decode() for line in lines]


def get_running_windows() -> list:
    output = subprocess.check_output('wmctrl -lpG', shell=True)
    lines = output.splitlines()
    # The remainder of the line contains the window title (possibly with multiple spaces in the title).
    return [line.decode().split(maxsplit=8) for line in lines]


def has_any_running_window() -> bool:
    running_windows = get_running_windows()
    return len(running_windows) != 0


def close_window_gracefully_async(window_id: str):
    subprocess.Popen(['wmctrl', '-ic', window_id])


def close_window_gracefully_sync(window_id: str):
    subprocess.check_output(['wmctrl', '-ic', window_id])


def move_window_to(window_id: str, desktop_number: str):
    subprocess.Popen(['wmctrl', '-ir', window_id, '-t', desktop_number])


def is_gnome() -> bool:
    output = subprocess.check_output(['wmctrl', '-m'])
    lines = output.splitlines()
    wm_type = lines[0].decode().split(':')[1]
    if wm_type.strip() == 'GNOME Shell':
        return True
    return False

