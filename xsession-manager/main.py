import getpass
import os
import sys

from arguments_parser import ArgumentsParser
import arguments_handler


def run():
    parser = ArgumentsParser()
    args = parser.parse_arguments()
    print('Namespace object before handling by this program: ' + str(args))
    arguments_handler.check_and_reset_args(args)
    check_login_condition()
    arguments_handler.handle_arguments(args)


def check_login_condition():
    """
    1. Do not allow to execute this program under root account
    2. ss
    """
    if os.geteuid == 0:
        print("This program must be run as a normal user")
        sys.exit(1)

    original_login_user = os.getlogin()
    user = getpass.getuser()
    if original_login_user != user:
        print("This tool must be run under the login user's session. Maybe you are under a su login session?")
        sys.exit(1)





if __name__ == '__main__':
    run()
