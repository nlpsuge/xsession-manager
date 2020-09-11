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


def close_window_gracefully(window_id: str):
    subprocess.Popen(['wmctrl', '-ic', window_id])

