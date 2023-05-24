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
import csv
import os
import json
import sys

import dotenv
import notion_client

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

notion_keys = [
    'Part Number/title/0/plain_text',         # Part Number
    'Current Quantity/number',              # Quantity
    'Description/rich_text/0/plain_text'    # Description
]


def main(args):
    if not os.path.exists(args.bom):
        raise FileNotFoundError(args.bom)
    
    if not args.bom.lower().endswith('.csv'):
        raise ValueError(f'Filepath "{args.bom}" does not end in .csv')
    
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
    
    header_col_map = []
    for header in required_bom_fields:
        # Validate that all headers are in the provided BOM
        if header not in headers:
            raise ValueError(f'"{header}" was not found as a header in the BOM')
        # Create a mapping of header name to column index
        header_col_map.append(headers.index(header))

    # Not pythonic, but faster
    for header in required_bom_fields:
        header_col_map.append(-1 if header not in headers else headers.index(header))
        
    bom = []
    for row in bom_csv:
        # Skip rows that are blank/empty
        if len(row) == 0:
            continue
        bom_item = []
        bom.append(bom_item)
        # Reorder CSV data into template format
        for col in header_col_map:
            bom_item.append(row[col])
    return bom


def check_inventory(bom, search, decrement):
    if not search:
        return
    
    inv = inventory.list_db()
    #TODO finish

def check_jlc(bom, assembly):
    if not assembly:
        return
    
def check_digikey_mouser(bom):
    pass


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
    dotenv.load_dotenv()
    args = _parse_args()
    sys.exit(main(args))
