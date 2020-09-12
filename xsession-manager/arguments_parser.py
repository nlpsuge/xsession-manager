import argparse
import sys


class ArgumentsParser:

    def parse_arguments(self):
        parser = argparse.ArgumentParser(allow_abbrev=False)
        parser.add_argument('-s', '--save',
                            nargs='?',
                            help=
                            'Save the current session. Save to the default session if not specified a session name.')
        parser.add_argument('-c', '--close-all', action='store_true', help='Close the current session gracefully.')
        parser.add_argument('-r', '--restore',
                            nargs='?',
                            help='Restore a session gracefully. '
                                 'Restore the default session if not specified a session name.')
        parser.add_argument('-ri', '--restoring-interval', type=int,
                            default=2,
                            help='Specify the interval between restoring applications, in seconds. '
                                 'The default is 2 seconds. ')

        parser.add_argument('-p', action='store_true', help='Pop a dialog to ask user whether to restore a X session.')

        parser.add_argument('-l', '--list', action='store_true', help='List the sessions.')
        parser.add_argument('-t', '--detail', help='Check out the details of a session.')

        # -x [<window_id>|<pid>|<app_name> or <title_name>]
        parser.add_argument('-x', '--exclude',
                            # Require at least one value
                            nargs='+',
                            help='Exclude apps from the operation according to '
                                 '<window_id>, <pid>, <app_name> or <title_name>. '
                                 'Require at least one value')

        if len(sys.argv) == 1:
            print('No arguments provided.\n')
            parser.print_help(sys.stderr)
            sys.exit(1)

        return parser.parse_args()
