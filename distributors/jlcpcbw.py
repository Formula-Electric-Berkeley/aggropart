#!/usr/bin/env python3
"""
TODO add description
"""

import re

import bs4
import urllib.parse
import urllib.request
import js2py


class JLCItem:
    def __init__(self, nuxt_key, default):
        """TODO document"""
        self.nuxt_key = nuxt_key
        self.default = default


item_fields = {
    'JLCPCB Part Number': JLCItem('componentCode', ''),
    'Mfg Part Number': JLCItem('componentModelEn', ''),
    'Manufacturer': JLCItem('componentBrandEn', ''),
    'Stock': JLCItem('stockCount', 0),
    'Description': JLCItem('describe', '')
}


def search_items(keyword):
    urlsafe_keyword = urllib.parse.quote(keyword)
    url = f'https://jlcpcb.com/parts/componentSearch?searchTxt={urlsafe_keyword}'
    return _get_nuxt_part_data(url)


def get_item(part_number: str) -> dict:
    if len(part_number) == 0:
        # A blank part number is not a valid JLC search
        return {}
    url = f'https://jlcpcb.com/partdetail/{part_number}'
    return _get_nuxt_part_data(url)[0]


def _get_nuxt_part_data(url: str) -> list[dict]:
    req = urllib.request.urlopen(url)
    resp = req.read()
    parser = bs4.BeautifulSoup(resp, features='html.parser')
    nuxt_script = parser.find('script', text=re.compile('.*__NUXT__.*'))
    nuxt_json = js2py.eval_js(nuxt_script.text)
    parts = nuxt_json['data'][0]['presaleTypeTabs'][0]['tableInfo']['tableList']
    return [_filter_item(part) for part in parts]


def _filter_item(part):
    item = {}
    for field_name, field_value in item_fields.items():
        try:
            item[field_name] = part[field_value.nuxt_key]
        except (KeyError, IndexError, AttributeError):
            item[field_name] = field_value.default
    return item


if __name__ == "__main__":
    raise NotImplementedError()
# TODO give this file argparse, entrypoint, etc
