#!/usr/bin/env python3
"""
TODO add description
"""

import argparse
import os
import sys

import dotenv
import notion_client


_db_mappings = {
    'Part Number': 'Part Number/title/0/plain_text',
    'Quantity': 'Current Quantity/number',
    'Description': 'Description/rich_text/0/plain_text'
}

_db_inst = None
dotenv.load_dotenv()


def _item_is_valid(item):
    """User customizable function to filter out unwanted inventory entries."""
    # Equivalent to a blank Project property field (EECS inventory)
    return item['properties']['📽️ Projects']['id'] == 'fdLi'


def create_client():
    """Create a Notion API client using the environment's NOTION_TOKEN."""
    return notion_client.Client(auth=os.environ['NOTION_TOKEN'])


def get_db(client=create_client(), id=os.environ['NOTION_DB_ID'], force_refresh=False):
    """Get the specified database content by querying the Notion API."""
    global _db_inst
    if _db_inst is None or force_refresh:
        _db_inst = client.databases.query(id)['results']
    return _db_inst


def list_db(db=get_db()):
    """List all entries in the Notion database."""
    #TODO inventory caching
    inventory = []
    for item in db:
        if _item_is_valid(item):
            inv_item = {k: _get_inv_field(item['properties'], v) for k, v in _db_mappings.items()}
            if None not in inv_item:
                inventory.append(inv_item)
                #TODO make this CSV instead of JSON
    return inventory


def search_db(query, db=get_db()):
    """Search the database for a query and return all matching results."""
    #TODO implement
    raise NotImplementedError()


def update_db(query, quantity, db=get_db()):
    """Update the quantity of one database item by the quantity specified."""
    #TODO implement (will also require changing permissions on web mgmt ui)
    raise NotImplementedError()


def _get_inv_field(db, query):
    """#TODO document this"""
    try:
        keys = query.split('/')
        curr = db[keys.pop(0)]
        while len(keys) > 0:
            k = keys.pop(0)
            if k.isnumeric():
                k = int(k)
            curr = curr[k]
        return curr
    except TypeError:
        return None
    except IndexError:
        return None


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--token', '-t', help='Notion authentication token; required if not specified in .env')
    parser.add_argument('--dbid', '-d', help='Notion database ID; required if not specified in .env')
    op_subparser = parser.add_subparsers(dest='operation', required=True, help='type of desired operation')
    op_subparser.add_parser('list', description='List all items in inventory.')
    search_parser = op_subparser.add_parser('search', description='Search for an item in inventory.')
    search_parser.add_argument('query', help='query to search for in inventory')
    update_parser = op_subparser.add_parser('update', description='Update the quantity of one item currently in inventory.')
    update_parser.add_argument('query', help='query to identify part to be updated')
    update_parser.add_argument('quantity', help='**change** in quantity desired')

    args = parser.parse_args()

    _checkset_env('NOTION_TOKEN', args.token, 'Notion token')
    _checkset_env('NOTION_DB_ID', args.dbid, 'Notion database ID')

    if args.operation == 'list':
        return list_db()
    elif args.operation == 'search':
        return search_db(args.query)
    elif args.operation == 'update':
        return update_db(args.query, args.quantity)
    else:
        raise ValueError(f'"{args.operation}" was not recognized as a valid operation')


def _checkset_env(key, arg, designator):
    if key not in os.environ or len(os.environ[key]) == 0:
        if not arg:
            raise ValueError(f'No {designator} was specified.')
        os.environ[key] = arg
    elif arg:
        print(f'WARNING: {designator} was specified but overridden by entry in .env')


if __name__ == "__main__":
    sys.exit( _parse_args())
