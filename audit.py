#!/usr/bin/env python3
"""
Audit the total value and/or number of parts/containers in any number of boxes of EECS inventory.
"""

import argparse
import logging
import os
import sys

import common
import inventory
import popups

from distributors import digikeyw


def all_boxes(count, refresh=False):
    item_inv = inventory.list_db(inventory.get_db(db_id=os.environ['NOTION_INV_DB_ID'], force_refresh=refresh))
    if count:
        total_containers = len(item_inv)
        total_items = sum([item['Quantity'] for item in item_inv])
        return f'*** Total number of items in EECS inventory: {total_items} ({total_containers} containers) ***'
    else:
        total_value = calculate_value(item_inv)
        return f'*** Total value of all items in EECS inventory: ${total_value} ***'


def selected_boxes_gui(count, refresh=False):
    box = popups.input_('Box to query?')
    info = selected_boxes([box], count, refresh)
    popups.info(info)


def selected_boxes(boxes, count, refresh=False):
    item_inv = inventory.get_db(db_id=os.environ['NOTION_INV_DB_ID'], force_refresh=refresh)
    box_inv = inventory.get_db(db_id=os.environ['NOTION_BOX_DB_ID'], force_refresh=True)
    all_box_titles = [get_box_title(v) for v in box_inv]

    total_containers = 0
    total_items = 0
    selected_item_inv = []
    
    for desired_box_title in boxes:
        desired_box_title = f'EECS Box {desired_box_title}'
        if desired_box_title not in all_box_titles:
            logging.warning(f'WARNING: {desired_box_title} not found in all inventory boxes. Ignoring.')
            continue

        for box in box_inv:
            box_title = get_box_title(box)
            if box_title == desired_box_title:
                raw_relations = inventory.get_page_property(box['id'], 'RBxL')
                relations = [v['relation']['id'] for v in raw_relations['results']]
                logging.info(f'Number of containers in box {box_title}: {len(relations)}')
                total_containers += len(relations)

                items_in_box = 0
                for r in relations:
                    item = find_item_by_id(item_inv, r)
                    if item is not None:
                        items_in_box += get_item_qty(item)
                        selected_item_inv.append(item)
                logging.info(f'Number of items in box {box_title}: {items_in_box}')
                total_items += items_in_box
                break
    
    if count:
        return f'*** Total number of items in EECS box(es) {", ".join(boxes)}: {total_items} ({total_containers} containers) ***'
    else:
        total_value = calculate_value(inventory.list_db(selected_item_inv))
        return f'*** Total value of items in EECS box(es) {", ".join(boxes)}: ${total_value} ***'


def get_item_qty(item, default=0):
    qty = item['properties']['Current Quantity']['number']
    return qty if qty is not None else default


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
            part_num = item['Description'] if len(item['Description']) > 0 else part_num
        if len(part_num) == 0:
            continue
        dk_query = digikeyw.search_items(part_num)
        if dk_query is None:
            continue
        if len(dk_query.exact_manufacturer_products) > 0:
            dk_part = dk_query.exact_manufacturer_products[0]
            item_value = round(dk_part.unit_price * item['Quantity'], 4)
            total_value += item_value
            logging.info(f'Value of item {part_num}: ${dk_part.unit_price} x {item["Quantity"]} = ${item_value}')
    return round(total_value, 2)
    

def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--count', action='store_true', help='count items only, do not query value')
    parser.add_argument('-r', '--refresh', action='store_true', default=False, help='force refresh the inventory')
    parser.add_argument('boxes', nargs='*', help='EECS box names to audit (e.x. XS0001); query all by default')

    args = parser.parse_args()

    if len(args.boxes) == 0:
        logging.info(all_boxes(args.count, args.refresh))
    else:
        logging.info(selected_boxes(args.boxes, args.count, args.refresh))


if __name__ == "__main__":
    common.init_env()
    sys.exit(_parse_args())