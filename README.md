# [save-restore-opened-apps](https://github.com/nlpsuge/MyShell/blob/master/save-restore-opened-apps)

Save running X applications, and then reopen them all later. This tool relies on [wmctrl](http://tripie.sweb.cz/utils/wmctrl/).

## Install
```bash
git clone https://github.com/nlpsuge/save-restore-opened-apps.git
cd save-restore-opened-apps
chmod +x save-restore-opened-apps
# then copy save-restore-opened-apps to somewhere you like, eg /usr/local/bin
cp save-restore-opened-apps /usr/local/bin
```

## Usage:

### Save running X applications
```bash
save-restore-opened-apps -s
```
or
```bash
save-restore-opened-apps --save
```

### Reopen them all
```bash
save-restore-opened-apps -r
```
or
```bash
save-restore-opened-apps --reopen
```
or pop a dialog to ask to restore the previous working state. Note that the default countdown is 5 seconds.
```bash
save-restore-opened-apps -d
```

### Close all windows
```bash
save-restore-opened-apps -C
```
or
```bash
save-restore-opened-apps --close-all
```

### List saved apps
```bash
save-restore-opened-apps -l
```
or
```bash
save-restore-opened-apps --list
```
## Do you want to auto restore the previous working state after login?
Here is a solution. If you are using Fedora, create a file named ```auto-restore-working-state.desktop``` and the ```Exec``` should be:
```bash
save-restore-opened-apps -d
```
Then put this file into ```~/.config/autostart```.

## Todo:
- [X] Reopen WINE-based application
- [ ] Avoid saving system's applications
