#!/usr/bin/env python3
"""
TODO add description
"""

import argparse
import pickle
import json
import sys

from cache import SingleCache
from distributors import digikeyw, mouserw

#TODO write comparison per part between Digikey and Mouser to find optimal split. 
# support theoretical discounts and mouser quotes;
# integrate with aggropart GUI (eventually)

UNAVAILABLE_ITEM_PRICE = '$1000000.00'
DK_SHIPPING = 6.99
DK_DISCOUNT = 0.1


class FilePart:
    def __init__(self, line):
        split = line.split(' ')
        self.part_num = split[0]
        self.qty = int(split[1])

class SourcedPart:
    def __init__(self, file_part, dk_part, mouser_part):
        self.file = file_part
        self.dk = dk_part
        self.mouser = mouser_part


_dk_cache = SingleCache('cache/compare_dk.json')
_mouser_cache = SingleCache('cache/compare_mouser.json')
# _newark_cache = Cache

def _update_dk(cache, key):
    item = digikeyw.get_item(key)
    cache[key] = (item, item.digi_key_part_number)


def _update_mouser(cache, key):
    item = mouserw.get_item(key)
    price_str = mouserw.get_or_default(item['PriceBreaks'], 0, {'Price': UNAVAILABLE_ITEM_PRICE})['Price']
    price = float(price_str[1:])
    mouser_pn = item['MouserPartNumber']
    cache[key] = (price, mouser_pn)


def get_mouser_ship_price(parts):
    cart_key = mouserw.create_cart()
    insert_parts = [mouserw.CartItem(p.mouser[1], p.file.qty) for p in parts]
    add_success = mouserw.add_items_to_cart(insert_parts, cart_key)
    if not add_success:
        print('Could not add items to cart')
        exit(1)
    with open('shipping_address.json', 'r') as f:
        shipping_address = json.load(f)
    shipping_methods = mouserw.get_shipping(shipping_address, cart_key)
    nonzero_shipping_methods = list(filter(lambda v: v[1] != 0, shipping_methods))
    return min(nonzero_shipping_methods, key=lambda v: v[1])


def main(args):
    with open(args.file, 'r') as f:
        lines = f.readlines()
    file_parts = [FilePart(line) for line in lines]

    mouser_cost = 0
    dk_cost = 0
    mouser_parts = []
    dk_parts = []
    for file_part in file_parts:
        dk_part = _dk_cache.get(file_part.part_num, _update_dk)
        mouser_part = _mouser_cache.get(file_part.part_num, _update_mouser)

        sourced_part = SourcedPart(file_part, dk_part, mouser_part)
        # TODO implement extended pricing (and accurate discount)
        if dk_part[0] <= mouser_part[0]:
            dk_parts.append(sourced_part)
            dk_cost += dk_part[0] * file_part.qty
        else:
            mouser_parts.append(sourced_part)
            mouser_cost += mouser_part[0] * file_part.qty
    
    mouser_ship_price = get_mouser_ship_price(mouser_parts)
    mouser_cost += mouser_ship_price[1]
    dk_cost *= (1 - DK_DISCOUNT)
    dk_cost += DK_SHIPPING

    print(f'{len(dk_parts)} Digikey parts (${round(dk_cost, 2)})')
    for part in dk_parts:
        print(f'{part.file.qty}x {part.dk[1]} (@${round(part.dk[0], 2)}/each vs ${round(part.mouser[0], 2)})')

    print(f'\n{len(mouser_parts)} Mouser parts (${round(mouser_cost, 2)})')
    for part in mouser_parts:
        print(f'{part.file.qty}x {part.mouser[1]} (@${round(part.mouser[0], 2)}/each vs ${round(part.dk[0], 2)})')


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', help='parts listing filepath, formatted in (part_num, qty) for each item')
    args = parser.parse_args()
    return main(args)

if __name__ == "__main__":
    sys.exit(_parse_args())