import argparse
import sys
from .version import __version__


class ArgumentsParser:

    def parse_arguments(self):
        parser = argparse.ArgumentParser(allow_abbrev=False)
        parser.add_argument('-s', '--save',
                            nargs='?',
                            help=
                            'Save the current session. Save to the default session if not specified a session name.')
        parser.add_argument('-c', '--close-all',
                            nargs='*',
                            help='Close the windows gracefully. '
                                 'Close all windows if only -c/--close-all is present. '
                                 'You can specify arguments to tell me which windows should be closed, '
                                 'that is <window_id>, <pid>, <app_name> or <title_name> exactly the same as -x.')
        parser.add_argument('-im', '--including-apps-with-multiple-windows',
                            action='store_true',
                            help='Close the windows gracefully including apps with multiple windows')
        parser.add_argument('-r', '--restore',
                            nargs='?',
                            help='Restore a session gracefully. '
                                 'Restore the default session if not specified a session name.')
        parser.add_argument('-ri', '--restoring-interval', type=int,
                            default=2,
                            help='Specify the interval between restoring applications, in seconds. '
                                 'The default is 2 seconds. ')

        parser.add_argument('-pr',
                            nargs='?',
                            help='Pop up a dialog to ask user whether to restore a X session.')

        parser.add_argument('-l', '--list', action='store_true', help='List the sessions.')
        parser.add_argument('-t', '--detail',
                            nargs='?',
                            help='Check out the details of a session.')

        # -x [<window_id>|<pid>|<app_name> or <title_name>]
        parser.add_argument('-x', '--exclude',
                            # Require at least one value
                            nargs='+',
                            help='Exclude apps from the operation according to '
                                 '<window_id>, <pid>, <app_name> or <title_name>. '
                                 'Require at least one value')
        # -i [<window_id>|<pid>|<app_name> or <title_name>]
        parser.add_argument('-i', '--include',
                            # Require at least one value
                            nargs='+',
                            help='Include apps from the operation according to '
                                 '<window_id>, <pid>, <app_name> or <title_name>. '
                                 'Require at least one value')

        parser.add_argument('-ma', '--move-automatically',
                            nargs='?',
                            help='Auto move windows to specified workspaces according to a saved session. '
                                 'The default session is `xsession-default`')

        parser.add_argument('-v', '--version',
                            action='version',
                            version=__version__)

        if len(sys.argv) == 1:
            print('No arguments provided.\n')
            parser.print_help(sys.stderr)
            sys.exit(1)

        return parser.parse_args()
