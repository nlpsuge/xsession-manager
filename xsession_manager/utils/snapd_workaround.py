# See:
# https://snapcraft.io/docs/snapd-api
# https://snapcraft.io/docs/snap-format
# https://snapcraft.io/docs/system-snap-directory

import json
import re
from typing import Dict, List

import pycurl

from . import gio_utils, suppress_output, string_utils


class Snapd:

    def __init__(self):
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.UNIX_SOCKET_PATH, '/run/snapd.socket')

    def get_app(self, app_name: str) -> List[Dict]:
        self.curl.setopt(pycurl.URL, 'http://localhost/v2/apps?names=%s' % app_name)
        try:
            r = self.curl.perform_rs()
        except:
            print("Failed to query the app named '%s' via /run/snapd.socket" % app_name)
            return []

        jr = json.loads(r)

        if jr['status-code'] == 200:
            result: List[Dict] = jr['result']
            return result

        print(jr['result']['message'])
        return []

    def get_app_re(self, app_name: str) -> dict:
        """
        Raise an error if more than one apps were found
        """
        result = self.get_app(app_name)
        if len(result) == 0:
            return {}
        if len(result) > 1:
            _r = [r for r in result if ('desktop-file' in r.keys()
                                        and not string_utils.empty_string(r['desktop-file']))]
            # Remove duplicates by desktop-file
            _r_duplicates_removed = list({_e['desktop-file']: _e for _e in _r}.values())
            if len(_r_duplicates_removed) == 0:
                return {}
            elif len(_r_duplicates_removed) == 1:
                return _r_duplicates_removed[0]
            if len(_r_duplicates_removed) > 1:
                message = 'Found multiple desktop files (%s) according to "%s", use the first one (%s)'\
                          % (_r_duplicates_removed, app_name, _r_duplicates_removed[0]['desktop-file'])
                print(message)
                return _r_duplicates_removed[0]

        return result[0]

    @staticmethod
    def is_snap_app(app_cmd: str) -> (bool, str):
        # Visit https://regex101.com/r/SXUlVX/ to check the explanation of this regular expression pattern
        c = re.compile(r'([\/]|[\\]{,2})snap([\/]|[\\]{,2})[\w:\-]+([\/]|[\\]{,2})[\d]+')
        r = c.search(app_cmd)
        if r is not None:
            match = r.group()
            snap_app_name = re.split(r'[/|\\]+', match)[2]
            return True, snap_app_name
        return False, None

    def launch(self, app_names: List[str], suppress_stdout=True, suppress_stderr=True) -> bool:
        """
        Launch a application according to the app names.

        :param app_names: application name list
        :param suppress_stdout: suppress the stdout during the app launching
        :param suppress_stderr: suppress the stderr during the app launching
        :return: True if any one application listed in the app_names can be launched; False otherwise.
        """
        for app_name in app_names:
            app = self.get_app_re(app_name)
            if len(app) == 0:
                continue
            df = app['desktop-file']
            so = suppress_output.SuppressOutput(suppress_stdout, suppress_stderr)
            with so.suppress_output():
                return gio_utils.GDesktopAppInfo.launch_app_via_desktop_file(df)

        print('Failed to run apps %s as a Snap app' % app_names)
