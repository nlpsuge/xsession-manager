import argparse


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

        parser.add_argument('-p', action='store_true', help='Pop a dialog to ask user whether to restore a X session.')

        parser.add_argument('-l', '--list', action='store_true', help='List the sessions.')
        parser.add_argument('-t', '--detail', help='Check out the details of a session.')

        return parser.parse_args()