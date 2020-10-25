# See:
# https://snapcraft.io/docs/snapd-api
# https://snapcraft.io/docs/snap-format
# https://snapcraft.io/docs/system-snap-directory

import json
import re
from typing import Dict, List

import pycurl

from utils import gio_utils, suppress_output
from utils.exceptions import MoreThanOneAppsFound


class Snapd:

    def __init__(self):
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.UNIX_SOCKET_PATH, '/run/snapd.socket')

    def get_app(self, app_name) -> List[Dict]:
        self.curl.setopt(pycurl.URL, 'http://localhost/v2/apps?names=%s' % app_name)
        r = self.curl.perform_rs()
        jr = json.loads(r)

        if jr['status-code'] == 200:
            result: List[Dict] = jr['result']
            return result

        print(jr['result']['message'])
        return []

    def get_app_re(self, app_name) -> dict:
        """
        Raise an error if more than one apps were found
        """
        result = self.get_app(app_name)
        if len(result) == 0:
            return {}
        if len(result) > 1:
            raise MoreThanOneAppsFound()
        return result[0]

    @staticmethod
    def is_snap_app(app_cmd: str):
        # Visit https://regex101.com/r/SXUlVX/ to check the explanation of this regular expression pattern
        c = re.compile(r'([\/]|[\\]{,2})snap([\/]|[\\]{,2})[\w:\-]+([\/]|[\\]{,2})[\d]+')
        return c.search(app_cmd) is not None

    def launch(self, app_names: List[str]) -> bool:
        """
        Launch a application according to the app names.
        :param app_names: application name list
        :return: True if any one application listed in the app_names can be launched; False otherwise.
        """
        for app_name in app_names:
            app = self.get_app_re(app_name)
            if len(app) == 0:
                continue
            df = app['desktop-file']
            so = suppress_output.SuppressOutput()
            so.suppress_stderr = True
            so.suppress_stdout = True
            with so.suppress_output():
                return gio_utils.GDesktopAppInfo.launch_app_via_desktop_file(df)

        print('Failed to run apps %s as a Snap app' % app_names)
