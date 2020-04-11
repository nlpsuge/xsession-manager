# [xsession-manager](https://github.com/nlpsuge/MyShell/blob/master/xsession-manager)

Save X session and restore it later. This tool relies on [wmctrl](http://tripie.sweb.cz/utils/wmctrl/).

## Install
```bash
git clone https://github.com/nlpsuge/xsession-manager.git
cd xsession-manager
chmod +x xsession-manager
# Then copy xsession-manager to somewhere you prefer, like /usr/local/bin.
cp xsession-manager /usr/local/bin
```

## Usage:

### Save the current X session
```bash
xsession-manager -s
```
or
```bash
xsession-manager --save
```

### Restore the previous X session
```bash
xsession-manager -r
```
or
```bash
xsession-manager --reopen
```
or pop a dialog to ask to restore the previous X session. 
Note that the default countdown is 5 seconds giving you some time to cancel this operation.
```bash
xsession-manager -d
```

### Close all windows
```bash
xsession-manager -C
```
or
```bash
xsession-manager --close-all
```

### List the details of the previous X session
```bash
xsession-manager -l
```
or
```bash
xsession-manager --list
```
## If you want to restore the previous X session automatically after login
Here is a solution. If you are using Fedora, create a file named ```auto-restore-working-state.desktop``` and the ```Exec``` should be:
```bash
xsession-manager -d
```
Then put this file into ```~/.config/autostart```.

## Todo:
- [X] Support WINE-based application
- [ ] Avoid saving system's applications
