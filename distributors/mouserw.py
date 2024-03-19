#!/usr/bin/env python3
"""
TODO add description
"""

import uuid
import os

import requests

TIMEOUT = 10


fake_response_item = {
    'MouserPartNumber': '',
    'ManufacturerPartNumber': '',
    'Manufacturer': '',
    'Description': '',
    'Availability': '',
    'PriceBreaks': [
        {
            'Quantity': '',
            'Price': '',
        }
    ],
    'DataSheetUrl': '',
    'ProductDetailUrl': ''
}

class CartItem:
    def __init__(self, mouser_part_number, qty):
        self.mouser_part_number = mouser_part_number
        self.qty = int(qty)

    def json(self):
        return {
            "MouserPartNumber": self.mouser_part_number,
            "Quantity": self.qty
        }


def get_order_items(order_id):
    url = make_req_url('/api/v1/orderhistory/salesOrderNumber', {'salesOrderNumber': order_id}, True)
    resp = requests.get(url=url, timeout=TIMEOUT)
    return [] if resp.status_code != 200 else resp.json()['OrderLines']


def search_items(keyword, max_items=10):
    body = {
      "SearchByKeywordRequest": {
        "keyword": keyword,
        "records": max_items,
        "startingRecord": 0
      }
    }
    url = make_req_url('/api/v1/search/keyword')
    resp = requests.post(url=url, json=body, timeout=TIMEOUT)
    return resp.json()['SearchResults']['Parts']


def get_item(part_number):
    body = {
      "SearchByPartRequest": {
        "mouserPartNumber": part_number
      }
    }
    url = make_req_url('/api/v1/search/partnumber')
    resp = requests.post(url=url, json=body, timeout=TIMEOUT)
    resp_json = resp.json()
    if 'SearchResults' in resp_json and resp_json['SearchResults']:
        return resp_json['SearchResults']['Parts'][0]
    else:
        return None


def create_cart():
    cart_key = str(uuid.uuid4())
    params = {
        'cartKey': cart_key,
        'countryCode': 'US',
        'currencyCode': 'USD',
    }
    url = make_req_url('/api/v1/cart', params)
    requests.get(url=url, timeout=TIMEOUT)
    return cart_key


def add_items_to_cart(items, cart_key):
    body = {
        "CartKey": cart_key,
        "CartItems": [item.json() for item in items]
    }
    params = {
        'countryCode': 'US',
        'currencyCode': 'USD',
    }
    url = make_req_url('/api/v1/cart/items/insert', params, order_req=True)
    resp = requests.post(url=url, json=body, timeout=TIMEOUT)
    return resp.status_code == 200


def get_shipping(shipping_address, cart_key):
    body = {
        "OrderInitialize": {
            "ShippingAddress": shipping_address,
            "CurrencyCode": "USD",
            "CartKey": cart_key
        }
    }
    url = make_req_url('/api/v1/order/options/query', order_req=True)
    resp = requests.post(url=url, json=body, timeout=TIMEOUT)
    resp_json = resp.json()
    ship_methods = resp_json['OrderInitialize']['Shipping']['Methods']
    return [(m['Method'], m['Rate']) for m in ship_methods]


def make_req_url(endpoint, params=dict(), order_req=False):
    key = os.environ['MOUSER_ORDER_API_KEY' if order_req else 'MOUSER_PART_API_KEY']
    param_str = '&'.join([f'{k}={v}' for k, v in params.items()])
    return f'https://api.mouser.com{endpoint}?apiKey={key}&version=1{param_str}'


def format_item(item):
    return {
        'Mouser Part Number': item['MouserPartNumber'],
        'Mfg Part Number': item['ManufacturerPartNumber'],
        'Manufacturer': item['Manufacturer'],
        'Description': item['Description'],
        'Quantity Available': ''.join(filter(str.isdigit, item['Availability'])),
        'Minimum Order Quantity': get_or_default(item['PriceBreaks'], 0, {'Quantity': 'N/A'})['Quantity'],
        'Unit Price': get_or_default(item['PriceBreaks'], 0, {'Price': 'N/A'})['Price'],
        'Datasheet URL': item['DataSheetUrl'],
        'Mouser URL': item['ProductDetailUrl'],
    }


def get_or_default(lst, idx, default):
    try:
        return lst[idx]
    except IndexError:
        return default


if __name__ == "__main__":
    raise NotImplementedError()
# TODO give this file argparse, entrypoint, etc
