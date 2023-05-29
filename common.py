import json


def pfmt(obj):
    return json.dumps(obj, indent=4)


def pprint(obj):
    print(pfmt(obj))


def wait_resp(prompt, responses):
    """Wait for the user to enter one of a specific set of responses to a given prompt."""
    for idx in range(len(responses)):
        # Ensure all responses are in string format
        responses[idx] = str(responses[idx])
    wildcard = "*" in responses
    while True:
        resp = input(f'{prompt} {responses}: ')
        if resp in responses or wildcard:
            return resp
        else:
            print(f'Please answer from {responses}.')


def wait_yn(prompt):
    """Wait for the user to enter y or n to a given prompt."""
    while True:
        resp = input(f'{prompt} [y/n]: ')
        if resp == 'n':
            return False
        elif resp == 'y':
            return True
        else:
            print('Please answer [y/n].')
