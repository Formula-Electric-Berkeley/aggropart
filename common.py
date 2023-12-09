import json
import os

import dotenv


version = 'v0.1.1'


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
            raise ValueError(f'No {designator} was specified.')
        os.environ[key] = arg
    elif arg:
        print(f'WARNING: {designator} was specified but overridden by entry in .env')


def init_dotenv():
    dotenv.load_dotenv()
    os.makedirs(os.environ['DIGIKEY_STORAGE_PATH'], exist_ok=True)