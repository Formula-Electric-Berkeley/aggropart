#!/usr/bin/env python3
"""
Automatically queries, inventories, and labels items purchased from Digikey and Mouser.
"""

import argparse
import os
import sys

import common
import inventory

from distributors import digikeyw

#TODO program that tallies items for a box: # of bags, # of items (i.e 100 resistors in a bag = 100 items), total price


def main(args):
    if len(args.boxes) == 0:
        item_inv = inventory.list_db(inventory.get_db(db_id=os.environ['NOTION_INV_DB_ID']))#, force_refresh=True)
        total_value = calculate_value(item_inv[:3])
        print(f'***** Total value of all items in EECS inventory: ${total_value} *****')
    else:
        box_inv = inventory.get_db(db_id=os.environ['NOTION_BOX_DB_ID'], force_refresh=True)
        common.pprint(box_inv[0])
        common.pprint(box_inv[0]['properties']['Part Number']['title'][0]['plain_text'])
        total_value = calculate_value(box_inv)
        print(f'***** Total value of items in EECS box(es) {args.boxes}: ${total_value} *****')


def calculate_value(inv):
    total_value = 0
    for item in inv:
        part_num = item['Part Number']
        if part_num.startswith('CAP ') or part_num.startswith('RES '):
            # Part Number (title) and description are swapped for passives
            part_num = item['Description']
        dk_query = digikeyw.search_items(part_num)
        if len(dk_query.exact_manufacturer_products) > 0:
            dk_part = dk_query.exact_manufacturer_products[0]
            item_value = (dk_part.unit_price * item['Quantity'])
            total_value += item_value
            print(f'Value of item {part_num}: ${dk_part.unit_price} x {item["Quantity"]} = {item_value}')
    return round(total_value, 2)
    
def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('boxes', nargs='*', help='EECS box names to audit (e.x. XS0001)')

    args = parser.parse_args()
    return main(args)


if __name__ == "__main__":
    common.init_dotenv()
    sys.exit(_parse_args())