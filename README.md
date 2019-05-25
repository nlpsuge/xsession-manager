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

## Usage:<br />

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

### List saved apps
```bash
save-restore-opened-apps -l
```
or
```bash
save-restore-opened-apps --list
```

## Todo:
- [X] Reopen WINE-based application
- [ ] Avoid to save system's applications
