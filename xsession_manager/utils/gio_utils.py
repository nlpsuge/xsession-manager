import threading
from typing import List, Dict

import gi
from gi.overrides.Gio import Settings
from gi.repository.Gio import DesktopAppInfo

from ..settings import constants
from . import suppress_output
from .exceptions import MoreThanOneResultFound


class _DesktopAppInfoObject:

    app_id: str
    commandline: str


class GSettings:

    def __init__(self,
                 access_dynamic_workspaces=False,
                 access_num_workspaces=False):

        if access_dynamic_workspaces:
            self.schema_dynamic_workspaces = Settings.new(constants.GSettings.dynamic_workspaces.schema)
        if access_num_workspaces:
            self.schema_num_workspaces = Settings.new(constants.GSettings.workspaces_number.schema)

    def is_dynamic_workspaces(self) -> bool:
        return self.schema_dynamic_workspaces.get_boolean(constants.GSettings.dynamic_workspaces.key)

    def disable_dynamic_workspaces(self):
        self.schema_dynamic_workspaces.set_boolean(constants.GSettings.dynamic_workspaces.key, False)

    def enable_dynamic_workspaces(self):
        self.schema_dynamic_workspaces.set_boolean(constants.GSettings.dynamic_workspaces.key, True)

    def set_workspaces_number(self, workspaces_number: int):
        """
        Must set dynamic-workspaces to false before setting the new value of num-workspaces,
        or the change will not take effect.

        :param workspaces_number: the total number of workspaces
        """
        self.schema_num_workspaces.set_int(constants.GSettings.workspaces_number.key, workspaces_number)

    def get_workspaces_number(self) -> int:
        return self.schema_num_workspaces.get_int(constants.GSettings.workspaces_number.key)


class GDesktopAppInfo:

    def __init__(self):
        # Cache all .desktop files info in this OS
        self._all_desktop_apps_info_cache: List[DesktopAppInfo] = []

    @staticmethod
    def launch_app_via_desktop_file(desktop_file_path) -> bool:
        launcher: DesktopAppInfo = DesktopAppInfo().new_from_filename(desktop_file_path)
        launched = launcher.launch()
        return launched

    def launch_app(self, app_name: str) -> bool:
        """
        Launch an app according to a name by performing fuzzy string searching.

        Multiple desktop files could be found. The current strategy is launching the matched desktop file if and only if
        finds one result.

        :param app_name: The name of a application which is to be launched.
                         It can be a partial name, like 'spotify' and 'com.spotify.Client'
        :return:
        """
        desktop_apps: List[_DesktopAppInfoObject] = self.search_apps_fuzzily(app_name)
        if len(desktop_apps) == 1:
            desktop_app_info = DesktopAppInfo().new(desktop_apps[0].app_id)
            if desktop_app_info is None:
                print('No valid result found according to %s' % app_name)
                return False

            so = suppress_output.SuppressOutput(True, True)
            with so.suppress_output():
                return desktop_app_info.launch()
        elif len(desktop_apps) == 0:
            print('No result found according to %s' % app_name)
            return False
        else:
            commandlines = []
            for desktop_app in desktop_apps:
                desktop_app_info: DesktopAppInfo = DesktopAppInfo().new(desktop_app.app_id)
                if desktop_app_info is None:
                    continue
                commandline = desktop_app_info.get_commandline()
                commandlines.append(commandline)

            if len(set(commandlines)) == 1:
                desktop_app_info: DesktopAppInfo = DesktopAppInfo().new(desktop_apps[0].app_id)
                if desktop_app_info is None:
                    print('No valid result found according to %s' % app_name)
                    return False

                so = suppress_output.SuppressOutput(True, True)
                with so.suppress_output():
                    return desktop_app_info.launch()

            raise MoreThanOneResultFound('Multiple desktop files (%s) were found according to %s'
                                         % ([desktop_app.app_id for desktop_app in desktop_apps], app_name))

    def search_apps_fuzzily(self, app_name) -> List[_DesktopAppInfoObject]:
        """
        Perform searching fuzzily due to the method of DesktopAppInfo.search() lacks this ability.

        For more information please visit https://gitlab.gnome.org/GNOME/glib/-/issues/2232 and it's related issues.
        """

        with threading.RLock():
            if len(self._all_desktop_apps_info_cache) == 0:
                desktop_apps: List[DesktopAppInfo] = DesktopAppInfo().get_all()
                self._all_desktop_apps_info_cache = desktop_apps

        results: List[_DesktopAppInfoObject] = []
        for desktop_app in self._all_desktop_apps_info_cache:
            app_id = desktop_app.get_id()
            # do substring matching ignoring case
            if app_name.lower() in app_id.lower():
                daio = _DesktopAppInfoObject()
                daio.app_id = app_id
                daio.commandline = desktop_app.get_commandline()
                results.append(daio)

        return results

