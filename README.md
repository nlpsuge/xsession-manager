Some very useful Shells

# 1.[save-restore-opened-apps](https://github.com/nlpsuge/MyShell/blob/master/save-restore-opened-apps)

Save the current opened GUI applications. And re-open or restore them.

Usage:<br />
chmod +x save-restore-opened-apps<br />
#Save the current opened GUI applications<br />
./save-restore-opened-apps -s<br />
./save-restore-opened-apps --save<br />
#Re-open or restore them.<br />
./save-restore-opened-apps -r<br />
./save-restore-opened-apps --restore

Todo:
1. Need to handle WINE-based application
2. Need to avoid to save system's applications
