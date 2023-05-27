#!/usr/bin/env python3
"""
TODO add description
"""

# input Altium BOM
# validates all rows have Mouser, Digikey, JLC part numbers (or warn to ignore)
# Do inventory search (Notion) to see which parts are already available (& remove)
#  if None or multiple, ask user which is correct
#  if no box, warn & provide link for user - option for manual override
#  Subtract quantities from inventory if needed (& arg is passed)
# If assembly flag passed, (and API key provided)
#  search JLC and subtract all that are present
#  if a part is OOS, ask for alt part num or to buy externally
#  warn for extended parts (?)
#  tally part cost, parts to order from JLC
# For all remaining parts,
#  provide digikey and mouser part costs (for diff groupings)
#  user selects each src & qty (unless part only exists on one)
#  create importable BOM for Mouser and Digikey separately at end

import argparse
import copy
import csv
import json
import os
import sys
import time

from collections import namedtuple

import inventory


required_bom_fields = [
    'Comment',
    'Quantity',
    'Digi-Key Part Number',
    'Mouser Part Number',
    'JLCPCB Part Number',
]

optional_bom_fields = [
    'Description',          # For manual review only
    'Designator',           # For manual review only
    # 'Revision Status',    #TODO doesn't work?
    'JLCPCB Part Type'      # Only matters for JLC price esimation
]

max_matches = 20


class Match:
    def __init__(self, bom_item, inv_item, inv_idx):
        self.bom_item = bom_item
        self.inv_item = inv_item
        self.inv_idx = inv_idx

    def copy(self):
        return Match(
            copy.deepcopy(self.bom_item), 
            copy.deepcopy(self.inv_item), 
            self.inv_idx
        )


def main(args):
    if not os.path.exists(args.bom):
        raise FileNotFoundError(args.bom)
    
    if not args.bom.lower().endswith('.csv'):
        raise ValueError(f'Filepath "{args.bom}" does not end in .csv')
    
    os.makedirs('out/', exist_ok=True)
    
    with open(args.bom, 'r') as bom_fh:
        bom = parse_altium_bom(bom_fh)
        check_inventory(bom, args.search_inventory, args.decrement_inventory)
        check_jlc(bom, args.assembly)
        check_digikey_mouser(bom)


def parse_altium_bom(fh):
    """Read and parse a BOM exported from Altium given a file handle."""
    bom_csv = csv.reader(fh)
    try:
        headers = next(bom_csv)
    except StopIteration:
        # Check that the header was read - i.e. the file is not already empty
        raise ValueError('BOM did not contain enough data / the data was invalid')
    
    item_template = {}
    for header in required_bom_fields:
        # Validate that all headers are in the provided BOM
        if header not in headers:
            raise ValueError(f'"{header}" was not found as a header in the BOM')
        # Create a mapping of header name to column index
        item_template[header] = None

    # Not pythonic, but faster
    for header in optional_bom_fields:
        item_template[header] = None if header in headers else -1
        
    bom = []
    for row in bom_csv:
        # Skip rows that are blank/empty
        if len(row) == 0:
            continue
        bom_item = item_template.copy()
        bom.append(bom_item)
        # Reorder CSV data into template format
        for k in bom_item.keys():
            attribute = row[headers.index(k)]
            if attribute.isnumeric():
                attribute = int(attribute)
            bom_item[k] = attribute
    return bom[:5]


def check_inventory(bom, search, decrement):
    #TODO decrement from inventory
    if not search:
        return
    
    inv = inventory.list_db()
    print(f'Found {len(inv)} inventory item entries')
    found_items = []
    for bom_idx, bom_item in enumerate(bom[:]):
        matches = []
        for inv_idx, inv_item in enumerate(inv):
            if _has_matching_properties(bom_item, inv_item) and \
                    (inv_item['Quantity'] >= bom_item['Quantity']):
                matches.append(Match(bom_item, inv_item, inv_idx))

        proc_matches(bom, inv, bom_item, bom_idx, found_items, matches)

    inv_out_fn = 'out/from_inventory.json'
    if os.path.exists(inv_out_fn):
        resp = wait_yn('WARNING: Output path already exists. Overwrite?')
        if not resp:
            raise FileExistsError('User did not override existing file')
    with open(inv_out_fn, 'w') as fp:
        json.dump([match.inv_item for match in found_items], fp, indent=4)
    print(len(inv))


def proc_matches(bom, inv, bom_item, bom_idx, found_items, matches):
    if len(matches) == 1:
        match = matches[0]
        print('====================')
        print(f'Matched BOM part ({bom_idx}/{len(bom)})')
        print(json.dumps(match.bom_item, indent=4))
        print(f'with inventory part ({match.inv_idx}/{len(inv)})')
        print(json.dumps(match.inv_item, indent=4))
        print('====================')
        resp = wait_yn('Is this correct?')
        if resp:
            found_items.append(match.copy())
            found_items[-1].inv_item['Quantity'] = 1
            _decr_from_inv(inv, match.inv_item, match.inv_idx)
        else:
            manual_search = wait_resp('Enter a search term to look through inventory manually, or leave blank to skip.', ['*'])
            if len(manual_search) != 0:
                matches = _get_matching_inv(inv, manual_search, bom_item)
                proc_matches(bom, inv, bom_item, bom_idx, found_items, matches)
    elif len(matches) == 0:
        print('====================')
        print(f'No inventory matches found for ({bom_idx}/{len(bom)})')
        print(json.dumps(bom_item, indent=4))
        print('====================')
        manual_search = wait_resp('Enter a search term to look through inventory manually, or leave blank to skip.', ['*'])
        if len(manual_search) != 0:
            matches = _get_matching_inv(inv, manual_search, bom_item)
            proc_matches(bom, inv, bom_item, bom_idx, found_items, matches)
    else:
        print('====================')
        print(f'Found {len(matches)} matching inventory parts for BOM part ({bom_idx}/{len(bom)})')
        print(json.dumps(matches[0].bom_item, indent=4))
        print('Matching inventory parts')
        for match_idx, match in enumerate(matches):
            print(f'{match_idx}: (inventory item #{match.inv_idx}/{len(inv)}): {json.dumps(match.inv_item, indent=4)}')
        print('====================')
        sel_idx = wait_resp('Enter the index of the chosen inventory item (-1 to skip/manual search)', list(range(len(matches))) + [-1])
        sel_idx = int(sel_idx)
        if sel_idx == -1:
            manual_search = wait_resp('Enter a search term to look through inventory manually, or leave blank to skip.', ['*'])
            if len(manual_search) != 0:
                matches = _get_matching_inv(inv, manual_search, bom_item)
                proc_matches(bom, inv, bom_item, bom_idx, found_items, matches)
        else:
            found_items.append(matches[sel_idx].copy())
            found_items[-1].inv_item['Quantity'] = 1
            _decr_from_inv(inv, matches[sel_idx].inv_item, matches[sel_idx].inv_idx)


def _decr_from_inv(inv, inv_item, inv_item_idx):
    inv[inv_item_idx]["Quantity"] -= 1
    #TODO page qty update logic
    if inv[inv_item_idx]["Quantity"] <= 0:
        inv.remove(inv_item)
        #TODO page delete logic


def _has_matching_properties(bom_item, inv_item):
    for bom_attr_val in bom_item.values():
        for inv_attr_val in inv_item.values():
            if type(bom_attr_val) == str and type(inv_attr_val) == str and \
                    len(bom_attr_val) > 0 and len(inv_attr_val) > 0 and \
                    (bom_attr_val in inv_attr_val or inv_attr_val in bom_attr_val):
                return True
    return False


def _get_matching_inv(inv, to_match, bom_item):
    matches = []
    for inv_idx, inv_item in enumerate(inv):
        for inv_attr_val in inv_item.values():
            if type(inv_attr_val) == str and len(inv_attr_val) != 0 and \
                (to_match in inv_attr_val or inv_attr_val in to_match):
                matches.append(Match(bom_item, inv_item, inv_idx))
                break
        if len(matches) >= max_matches:
            break
    return matches


def check_jlc(bom, assembly):
    if not assembly:
        return


def check_digikey_mouser(bom):
    pass


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


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bom', help='filepath of Bill of Materials exported from Altium')
    parser.add_argument('--search-inventory', '-s',
                        action='store_true', 
                        default=True,
                        help='search the inventory for existing parts')
    parser.add_argument('--decrement-inventory', '-d',
                        action='store_true',
                        default=False,
                        help='decrement quantity of inventory items used in BOM')
    parser.add_argument('--assembly', '-a', 
                        action='store_true',
                        default=False,
                        help='use JLCPCB assembly service and parts')
    #TODO validate
    parser.add_argument('--validate-only', '-v',
                        action='store_true',
                        default=False,
                        help='validate that the BOM contains the right data ONLY')
    return parser.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(args))
