# [xsession-manager](https://github.com/nlpsuge/xsession-manager)

Save and restore windows for X11 desktop environment like Gnome, and many other features.

This project was written in ```Bash``` originally. But now I'm completely rewriting it in ```Python```
which obviously makes it way more flexible, extensible.

[![Downloads](https://pepy.tech/badge/xsession-manager/month)](https://pepy.tech/project/xsession-manager)
[![Supported Versions](https://img.shields.io/pypi/pyversions/xsession-manager.svg)](https://pypi.org/project/xsession-manager)
[![Pypi Versions](https://img.shields.io/pypi/v/xsession-manager.svg)](https://pypi.python.org/pypi/xsession-manager)
[![Contributors](https://img.shields.io/github/contributors/nlpsuge/xsession-manager.svg)](https://github.com/nlpsuge/xsession-manager/graphs/contributors)

## Install
### Install dependencies
+ Fedora
```Bash
dnf install python3-devel python3-tkinter wmctrl
```
### Install [xsession-manager](https://pypi.org/project/xsession-manager) via PyPi
```Bash
pip3 install xsession-manager
```
### Install xsession-manager via source code
#### Method-1: Using pip. 
This method install xsession-manager in `~/.local/lib/python3.9/site-packages` if you are a normal user, in `/usr/local/lib/python3.9/site-packages` if you are root.
```Bash
cd the_root_of_source_code
pip install .
```
#### Method-2: Using setup.py
This method install xsession-manager in `/usr/local/lib/python3.9/site-packages`.
```Bash
cd the_root_of_source_code
sudo python3 setup.py install
```

## Common usage
+ Save running windows as a X session

Save all running GUI windows to `xsession-default`
```Bash
xsm -s
```

Specify a session name like, `my-session-name`, restore it later on by running `xsm -s my-session-name`. This feature should be very helpful when you have multiple tasks to do and each task needs different GUI apps.
```Bash
xsm -s my-session-name
```

Note: 
1. It will save some window states, which include Always on Top and Always on Visible Workspace and will be used when executing `xsm -r` or `xsm -ma`.

+ Close running windows except those apps with mutiple windows. It's better to leave them to the user to close by hand, some apps like JetBrain's IDEs may have their own session. 
```Bash
xsm -c
```
+ Close running windows include those apps with mutiple windows.
```Bash
xsm -c -im
```
+ Restore the saved X session

Restore all GUI apps using the saved session named `xsession-default`
```Bash
xsm -r
```
Restore `gnome-system-monitor` using the saved session named `my-session-name`
```Bash
xsm -r my-session-name -i gnome-system-monitor
```
+ Move running windows to their Workspaces according to the saved X session
```Bash
xsm -ma
```
+ List saved X sessions
```Bash
xsm -l
```
+ View the details of a saved X sessions
```Bash
xsm -t xsession-default
```


## Full usage:

```
usage: xsm [-h] [-s [SAVE]] [-c [CLOSE_ALL ...]] [-im] [-r [RESTORE]] [-ri RESTORING_INTERVAL] [-pr [PR]] [-l] [-t [DETAIL]]
           [-x EXCLUDE [EXCLUDE ...]] [-i INCLUDE [INCLUDE ...]] [-ma [MOVE_AUTOMATICALLY]] [--version] [-v] [-vv]

options:
  -h, --help            show this help message and exit
  -s [SAVE], --save [SAVE]
                        Save the current session. Save to the default session if not specified a session name.
  -c [CLOSE_ALL ...], --close-all [CLOSE_ALL ...]
                        Close the windows gracefully. Close all windows if only -c/--close-all present. Or close one or more
                        apps if arguments provided, which supports <window_id>, <pid>, <app_name> or <title_name> exactly the
                        same as -x. For example: `xsm -c gedit 23475 0x03e00004`
  -im, --including-apps-with-multiple-windows
                        Close the windows gracefully including apps with multiple windows
  -r [RESTORE], --restore [RESTORE]
                        Restore a session gracefully. Restore the default session if not specified a session name.
  -ri RESTORING_INTERVAL, --restoring-interval RESTORING_INTERVAL
                        Specify the interval between restoring applications, in seconds. The default is 2 seconds.
  -pr [PR]              Pop up a dialog to ask user whether to restore a X session.
  -l, --list            List the sessions.
  -t [DETAIL], --detail [DETAIL]
                        Check out the details of a session.
  -x EXCLUDE [EXCLUDE ...], --exclude EXCLUDE [EXCLUDE ...]
                        Exclude apps from the operation according to <window_id>, <pid>, <app_name> or <title_name>. Require
                        at least one value
  -i INCLUDE [INCLUDE ...], --include INCLUDE [INCLUDE ...]
                        Include apps from the operation according to <window_id>, <pid>, <app_name> or <title_name>. Require
                        at least one value
  -ma [MOVE_AUTOMATICALLY], --move-automatically [MOVE_AUTOMATICALLY]
                        Auto move windows to specified workspaces according to a saved session. The default session is
                        `xsession-default`
  --version             show program's version number and exit
  -v, --verbose         Print debugging information
  -vv                   Print more debugging information, could contain sensitive info

```

## If you want to restore the previous X session automatically after login
Here is a solution. If you are using Fedora, create a file named ```auto-restore-working-state.desktop``` and the ```Exec``` should be:
```bash
xsm -pr
```
Then put this file into ```~/.config/autostart```.

For example:
```
[Desktop Entry]
Name=Auto Restore saved X Windows
Comment=
Icon=
Exec=xsm -pr
Terminal=false
Type=Application
X-GNOME-Autostart-Delay=20
```

***NOTE: You can also use ```xsession-manager``` instead of ```xsm```.***

## Todo:
[TODO](https://github.com/nlpsuge/xsession-manager/blob/master/TODO.md)
