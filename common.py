from datetime import datetime
import json
import logging
import os
import sys

import dotenv


VERSION = 'v0.1.2'

LOG_FOLDER = 'logs'

_has_init = False


def pfmt(obj) -> str:
    return json.dumps(obj, indent=4)


def pprint(obj, fmt=pfmt) -> None:
    print(fmt(obj))


def wait_yn(prompt) -> bool:
    """Wait for the user to enter y or n to a given prompt."""
    while True:
        resp = input(f'{prompt} [y (default)/n]: ')
        if resp == 'n':
            return False
        elif resp == 'y':
            return True
        elif len(resp) == 0:
            return True
        else:
            print('Please answer [y/n].')


def checkset_env(key: str, arg: str, designator: str) -> None:
    if key not in os.environ or len(os.environ[key]) == 0:
        if not arg:
            logging.error(f'No {designator} was specified.')
            raise ValueError(f'No {designator} was specified.')
        os.environ[key] = arg
    elif arg:
        logging.warning(f'WARNING: {designator} was specified but overridden by entry in .env')


def _exception_logging_handler(type, value, tb):
    logging.exception("Uncaught exception: {0}".format(str(value)))
    sys.__excepthook__(type, value, tb)


def init_env():
    global _has_init
    if _has_init:
        return
    
    sys.excepthook = _exception_logging_handler

    dotenv.load_dotenv()
    os.makedirs(os.environ['DIGIKEY_STORAGE_PATH'], exist_ok=True)

    os.makedirs(LOG_FOLDER, exist_ok=True)
    current_dt = datetime.now().strftime('%Y_%m_%d %H_%M_%S')
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(f'{LOG_FOLDER}/aggropart {current_dt}.log', mode='w'),
            logging.StreamHandler()
        ]
    )
    # httpx has annoying error messages that we would like to suppress
    logging.getLogger('httpx').setLevel(logging.ERROR)

    _has_init = True
