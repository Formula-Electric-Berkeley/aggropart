#!/usr/bin/env python3
"""
TODO add description
"""

import argparse
import os
import sys

import dotenv
from notion_client import Client as NotionClient

import common
from cache import Cache

db_mappings = {
    'Part Number': 'db["properties"]["Part Number"]["title"][0]["plain_text"]',
    'Quantity': 'db["properties"]["Current Quantity"]["number"]',
    'Description': 'db["properties"]["Description"]["rich_text"][0]["plain_text"]',
    'Box': 'get_page(db["properties"]["Box"]["relation"][0]["id"], silent=True)'
           '["properties"]["Part Number"]["title"][0]["plain_text"]',
    'URL': 'db["url"]'
}

_db_cache = Cache(lambda db_id: f'cache/db_{db_id}.json', timeout_sec=10000)
_page_cache = Cache(lambda page_id: f'cache/page_{page_id}.json', timeout_sec=10000)
_client_inst = None
dotenv.load_dotenv()


def _item_is_valid(item: dict) -> bool:
    """User customizable function to filter out unwanted inventory entries."""
    # Equivalent to a blank Project property field (EECS inventory)
    return item['properties']['📽️ Projects']['id'] == 'fdLi'


def create_client(force_refresh: bool = False) -> NotionClient:
    """Create a Notion API client using the environment's NOTION_TOKEN."""
    global _client_inst
    if _client_inst is None or force_refresh:
        _client_inst = NotionClient(auth=os.environ['NOTION_TOKEN'])
    return _client_inst


def get_page(page_id: str, client: NotionClient = create_client(),
             force_refresh: bool = False, silent: bool = False) -> dict:
    """Get the specified page content by querying the Notion API."""
    def updater(cache, key: str):
        cache[key] = client.pages.retrieve(key)

    value, used_cached = _page_cache.get(page_id, updater, force_refresh)
    if used_cached and not silent:
        print(f"Using cached Notion page for ID: {page_id}")
    return value


def get_db(db_id: str = os.environ['NOTION_DB_ID'], client: NotionClient = create_client(),
           force_refresh: bool = False, silent: bool = False) -> dict:
    """Get the specified database content by querying the Notion API."""
    def updater(cache, key):
        if not silent:
            print(f"Executing initial Notion DB query", flush=True)
        query = client.databases.query(key, page_size=100)
        cache[key] = query['results']
        while query['has_more']:
            if not silent:
                print(f"Executing Notion DB query with cursor: {query['next_cursor']}", flush=True)
            query = client.databases.query(key, start_cursor=query['next_cursor'], page_size=100)
            cache[key].extend(query['results'])

    value, used_cached = _db_cache.get(db_id, updater, force_refresh)
    if used_cached and not silent:
        print(f"Using cached Notion database for ID: {db_id}")
    return value


def list_db(db: dict) -> list[dict]:
    """List all entries in the Notion database."""
    inventory = []
    for item in db:
        if _item_is_valid(item):
            inv_item = {k: _filter_inv_item(item, query) for k, query in db_mappings.items()}
            if None not in inv_item.values():
                inventory.append(inv_item)
    return inventory


def search_db(query, db):
    """Search the database for a query and return all matching results."""
    # TODO implement
    raise NotImplementedError()


def update_db(query, quantity, mode, db):
    """Update the quantity of one database item by the quantity specified."""
    # TODO implement
    raise NotImplementedError()


def insert_db(attributes, quantity, db):
    """Update the quantity of one database item by the quantity specified."""
    # TODO implement
    # TODO validate EECS box number - another request to notion to get
    raise NotImplementedError()


def _filter_inv_item(db: dict, query: str):
    """TODO document"""
    try:
        return eval(query)
    except (KeyError, IndexError):
        return ""


def _parse_args() -> str:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--token', '-t', help='Notion authentication token; required if not specified in .env')
    parser.add_argument('--dbid', '-d', help='Notion database ID; required if not specified in .env')
    parser.add_argument('--refresh', '-r', action='store_true', help='force refresh database cache')

    op_subparser = parser.add_subparsers(dest='operation', required=True, help='type of desired operation')
    op_subparser.add_parser('list', description='List all items in inventory.')
    search_parser = op_subparser.add_parser('search', description='Search for an item in inventory.')
    search_parser.add_argument('query', help='query to search for in inventory')

    update_parser = op_subparser.add_parser('update',
                                            description='Update the quantity of one item currently in inventory.')
    update_parser.add_argument('query', help='query to identify part to be updated')
    update_parser.add_argument('quantity', help='relative or absolute quantity desired')
    update_parser.add_argument('mode', choices=['relative', 'absolute'],
                               help='whether quantity specified is relative to current quantity '
                                    'or is the new absolute quantity')

    insert_parser = op_subparser.add_parser('insert', description='Insert a new item into inventory.')
    insert_parser.add_argument('part_number', help='manufacturer part number of the new item')
    insert_parser.add_argument('box', help='EECS box number new item will be inserted into')
    insert_parser.add_argument('quantity', help='absolute quantity of new item')
    insert_parser.add_argument('description', help='description of new item')

    args = parser.parse_args()
    return validate_args(args)


def validate_args(args) -> str:
    _checkset_env('NOTION_TOKEN', args.token, 'Notion token')
    _checkset_env('NOTION_DB_ID', args.dbid, 'Notion database ID')

    if args.operation in ('list', 'search', 'update', 'insert'):
        db = get_db(force_refresh=args.refresh)
        if args.operation == 'list':
            return common.pfmt(list_db(db))
        elif args.operation == 'search':
            return common.pfmt(search_db(args.query, db))
        elif args.operation == 'update':
            return common.pfmt(update_db(args.query, args.quantity, args.mode, db))
        elif args.operation == 'insert':
            # TODO fix this
            return common.pfmt(insert_db(args.part_number, args.quantity, args.description, db))
    else:
        raise ValueError(f'"{args.operation}" was not recognized as a valid operation')


def _checkset_env(key: str, arg: str, designator: str) -> None:
    """TODO document"""
    if key not in os.environ or len(os.environ[key]) == 0:
        if not arg:
            raise ValueError(f'No {designator} was specified.')
        os.environ[key] = arg
    elif arg:
        print(f'WARNING: {designator} was specified but overridden by entry in .env')


if __name__ == "__main__":
    sys.exit(_parse_args())
