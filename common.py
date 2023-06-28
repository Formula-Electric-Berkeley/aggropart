import json


def pfmt(obj) -> str:
    return json.dumps(obj, indent=4)


def pprint(obj) -> None:
    print(pfmt(obj))


def print_line() -> None:
    print('====================')


def wait_resp(prompt: str, choices):
    """Wait for the user to enter one of a specific set of responses to a given prompt."""
    for idx in range(len(choices)):
        # Ensure all responses are in string format
        choices[idx] = str(choices[idx])
    wildcard = "*" in choices
    while True:
        resp = input(f'{prompt} {choices}: ')
        if resp in choices or wildcard:
            return resp
        else:
            print(f'Please answer from {choices}.')


def wait_yn(prompt: str) -> bool:
    """Wait for the user to enter y or n to a given prompt."""
    while True:
        resp = input(f'{prompt} [y/n]: ')
        if resp == 'n':
            return False
        elif resp == 'y':
            return True
        else:
            print('Please answer [y/n].')
