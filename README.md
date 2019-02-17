Some very useful Shells

# 1.[save_restore_opened_apps](https://github.com/nlpsuge/MyShell/blob/master/save_restore_opened_apps)

Save the current opened GUI applications. And re-open or restore them.

Usage:<br />
chmod +x save_restore_opened_apps<br />
#Save the current opened GUI applications<br />
./save_restore_opened_apps -s<br />
./save_restore_opened_apps --save<br />
#Re-open or restore them.<br />
./save_restore_opened_apps -r<br />
./save_restore_opened_apps --restore

Todo:
1. Need to handle WINE-based application
2. Need to avoid to save system's applications
