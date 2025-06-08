"""
Automatically migrates INV1 (Notion) inventory items to INV2.
"""
import os

import requests

import common
from distributors import mouserw, digikeyw, jlcpcbw
import inventory


START_IDX = 873
GENERATE_BOXES = False
API_BASE = 'http://127.0.0.1:5000'


def main():
    # Form a mapping of box name to box ID
    if GENERATE_BOXES is True:
        # Generate new inventory boxes in INV2 from Notion Box DB
        box_db_id = os.environ['NOTION_BOX_DB_ID']
        boxes = inventory.list_db(inventory.get_db(box_db_id, force_refresh=True))

        box_map = {}
        for box in boxes:
            print(box)
            attrs = {
                'api_key': os.environ['INV2_BACKEND_API_KEY'],
                'name': box['Part Number']  # This formatting is weird but it works
            }
            resp = requests.post(f'{API_BASE}/api/box/create', data=attrs)
            print(resp.json())
            box_id = resp.json()['body'][0]['box_id']
            box_map[attrs['name']] = box_id
    else:
        # List the existing boxes in the inventory (INV2)
        box_map = {}
        api_key = os.environ['INV2_BACKEND_API_KEY']
        resp = requests.get(f'{API_BASE}/api/boxes/list?api_key={api_key}')
        for box in resp.json()['body']:
            box_map[box['name']] = box['box_id']

    # Get all items in INV1 (Notion)
    inv = inventory.list_db(inventory.get_db())

    # Skip to START_IDX in INV1 (restart mechanism, manual only)
    for i, item in enumerate(inv[START_IDX:]):
        mfg_part_num, desc = item['Part Number'], item['Description']
        # Swap manufacturer part number and description if CER or RES in mfg P/N (SMD components)
        if 'CER' in mfg_part_num or 'RES' in mfg_part_num:
            desc, mfg_part_num = mfg_part_num, desc

        # Get DK, Mouser, JLC part numbers for INV1 item
        digikey_resp = digikeyw.search_items(mfg_part_num).exact_manufacturer_products
        mouser_resp = mouserw.search_items(mfg_part_num)
        jlcpcb_resp = jlcpcbw.search_items(mfg_part_num)

        # Assemble attributes for INV2 item
        attrs = {
            'api_key': os.environ['INV2_BACKEND_API_KEY'],
            'box_id': box_map[item['Box']],
            'mfg_part_number': mfg_part_num,
            'quantity': item['Quantity'],
            'description': desc,
            'digikey_part_number': _get_with_default(digikey_resp, 0, lambda a: a.digi_key_part_number),
            'mouser_part_number': _get_with_default(mouser_resp, 0, lambda a: a['MouserPartNumber']),
            'jlcpcb_part_number': _get_with_default(jlcpcb_resp, 0, lambda a: a['JLCPCB Part Number'])
        }
        attrs = {k: _sanitize(v) for k, v in attrs.items()}
        print(i, attrs)

        # Post new item create to INV2
        resp = requests.post(f'{API_BASE}/api/item/create', data=attrs)
        if resp.status_code != 200:
            print(f'ERROR at {i}')
            break


def _get_with_default(lst, idx, subidx_func) -> str:
    """Get list[idx][subidx] with a default value if list[idx] is invalid"""
    return subidx_func(lst[idx]) if len(lst) > idx else ''


def _sanitize(v):
    """
    Sanitize some arbitrary value, ignoring if it is not a string.

    Unclean characters are replaced with empty string: \n, ?
    Smart quotes are replaced with normal double quotes
    """
    return v.replace('”', '"').replace('\n', ', ').replace('?', '') if isinstance(v, str) else v


if __name__ == '__main__':
    common.init_env()
    main()
