#!/usr/bin/env python3
"""
TODO add description
"""

import os

import requests


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


def search_items(keyword, max_items=10):
    body = {
      "SearchByKeywordRequest": {
        "keyword": keyword,
        "records": max_items,
        "startingRecord": 0
      }
    }
    url = make_req_url('/api/v1/search/keyword')
    resp = requests.post(url=url, json=body, timeout=10)
    return resp.json()['SearchResults']['Parts']


def get_item(part_number):
    body = {
      "SearchByPartRequest": {
        "mouserPartNumber": part_number
      }
    }
    url = make_req_url('/api/v1/search/partnumber')
    resp = requests.post(url=url, json=body, timeout=10)
    resp_json = resp.json()
    if 'SearchResults' in resp_json and resp_json['SearchResults']:
        return resp_json['SearchResults']['Parts'][0]
    else:
        return fake_response_item


def make_req_url(endpoint):
    return f'https://api.mouser.com{endpoint}?apiKey={os.environ["MOUSER_PART_API_KEY"]}&version=1'


def format_item(item):
    return {
        'Mouser Part Number': item['MouserPartNumber'],
        'Mfg Part Number': item['ManufacturerPartNumber'],
        'Manufacturer': item['Manufacturer'],
        'Description': item['Description'],
        'Quantity Available': ''.join(filter(str.isdigit, item['Availability'])),
        'Minimum Order Quantity': _get_or_default(item['PriceBreaks'], 0, {'Quantity': 'N/A'})['Quantity'],
        'Unit Price': _get_or_default(item['PriceBreaks'], 0, {'Price': 'N/A'})['Price'],
        'Datasheet URL': item['DataSheetUrl'],
        'Mouser URL': item['ProductDetailUrl'],
    }


def _get_or_default(lst, idx, default):
    try:
        return lst[idx]
    except IndexError:
        return default


if __name__ == "__main__":
    raise NotImplementedError()
# TODO give this file argparse, entrypoint, etc
