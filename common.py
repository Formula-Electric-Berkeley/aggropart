import json


version = 'v0.1.0'


def pfmt(obj) -> str:
    return json.dumps(obj, indent=4)


def pprint(obj) -> None:
    print(pfmt(obj))
