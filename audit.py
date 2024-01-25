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
        item_inv = inventory.list_db(inventory.get_db(db_id=os.environ['NOTION_INV_DB_ID']))
        total_value = calculate_value(item_inv)
        print(f'***** Total value of all items in EECS inventory: ${total_value} *****')
    else:
        item_inv = inventory.get_db(db_id=os.environ['NOTION_INV_DB_ID'])
        box_inv = inventory.get_db(db_id=os.environ['NOTION_BOX_DB_ID'], force_refresh=True)
        all_box_titles = [get_box_title(v) for v in box_inv]
        selected_item_inv = []

        for desired_box_title in args.boxes:
            desired_box_title = f'EECS Box {desired_box_title}'
            if desired_box_title not in all_box_titles:
                print(f'ERROR: {desired_box_title} not found in all inventory boxes. Ignoring.')
                continue

            for box in box_inv:
                if get_box_title(box) == desired_box_title:
                    raw_relations = inventory.get_page_property(box['id'], 'RBxL')
                    relations = [v['relation']['id'] for v in raw_relations['results']]
                    print(f'Number of items in box {get_box_title(box)}: {len(relations)}')
                    for r in relations:
                        item = find_item_by_id(item_inv, r)
                        if item is not None:
                            selected_item_inv.append(item)
                    break
                    
        total_value = calculate_value(inventory.list_db(selected_item_inv))
        print(f'***** Total value of items in EECS box(es) {", ".join(args.boxes)}: ${total_value} *****')


def get_box_title(box):
    return box['properties']['Part Number']['title'][0]['plain_text']


def find_item_by_id(inv, item_id):
    for item in inv:
        if item['id'] == item_id:
            return item


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
            item_value = round(dk_part.unit_price * item['Quantity'], 4)
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