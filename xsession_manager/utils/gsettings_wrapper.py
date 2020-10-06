import subprocess


def is_dynamic_workspaces() -> bool:
    output = subprocess.check_output(['gsettings', 'get', 'org.gnome.mutter', 'dynamic-workspaces'])
    lines = output.splitlines()
    return lines[0] == b'true'


def disable_dynamic_workspaces():
    subprocess.check_output(['gsettings', 'set', 'org.gnome.mutter', 'dynamic-workspaces', 'false'])


def enable_dynamic_workspaces():
    subprocess.check_output(['gsettings', 'set', 'org.gnome.mutter', 'dynamic-workspaces', 'true'])


def set_workspaces_number(workspaces_number: int):
    """
    Must set dynamic-workspaces to false before setting the new value of num-workspaces,
    or the change will not take effect.

    :param workspaces_number: the total number of workspaces
    """
    subprocess.check_output(['gsettings', 'set', 'org.gnome.desktop.wm.preferences', 'num-workspaces',
                            '%d' % workspaces_number])


def get_workspaces_number() -> int:
    output = subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.wm.preferences', 'num-workspaces'])
    lines = output.splitlines()
    return int(lines[0])
