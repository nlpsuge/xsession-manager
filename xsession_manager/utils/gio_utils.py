import gi
from gi.overrides.Gio import Settings
from gi.repository.Gio import DesktopAppInfo

from settings import constants


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

    @staticmethod
    def launch_app_via_desktop_file(desktop_file_path) -> bool:
        launcher: DesktopAppInfo = DesktopAppInfo().new_from_filename(desktop_file_path)
        launched = launcher.launch()
        return launched
