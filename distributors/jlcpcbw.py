#!/usr/bin/env python3
"""
TODO add description
"""

import re

import bs4
import urllib.parse
import urllib.request
import string
import js2py

COMPONENT_ID_ORDER = string.ascii_lowercase + string.ascii_uppercase + '_' + '$'


class JLCItem:
    def __init__(self, item_eval, search_eval, default):
        """TODO document"""
        self.item_eval = item_eval
        self.search_eval = search_eval
        self.default = default


# Fields to be parsed from each JLCPCB item
# Format: (eval_format_string, default_value)
item_fields = {
    'JLCPCB Part Number': JLCItem(
        '_item_metavals(parser)[2].text',
        '_find_by_class(parser, "item", "a").attrs.get("href").rsplit("/")[-1]',
        ''),
    'Mfg Part Number': JLCItem(
        '_item_metavals(parser)[1].text',
        r're.findall(r"\.*(\S+)\.*", _find_by_class(parser, "part-type", "a").text)[0]',
        ''),
    'Manufacturer': JLCItem(
        '_item_metavals(parser)[0].text',
        '_find_by_class(parser, "item", "div").text',
        ''),
    'Stock': JLCItem(
        'int(parser.find("div", class_="smt-count-component")'
        '.find("div", class_="text-16").text[len("In Stock: "):])',
        '_find_by_class(parser, "stock-item").text',
        0),
    'Description': JLCItem(
        '_item_metavals(parser)[4].text',
        '_find_by_class(parser, "item", "span").text',
        ''),
    'Package': JLCItem(
        '_item_metavals(parser)[3].text',
        '""',  # Not present for search
        ''),
}


def _item_metavals(parser: bs4.BeautifulSoup) -> bs4.ResultSet:
    #TODO fix this; the data-v-XXXX tag changes periodically
    return parser.find_all('div', {'data-v-71f56eca': True})


def _find_by_class(parser, classname, tag='div'):
    return parser.find(tag, {'class': classname})


def search_items(keyword):
    urlsafe_keyword = urllib.parse.quote(keyword)
    url = f'https://jlcpcb.com/parts/componentSearch?searchTxt={urlsafe_keyword}'
    req = urllib.request.urlopen(url)
    resp = req.read()
    parser = bs4.BeautifulSoup(resp, features='html.parser')
    # Typo from mountable to mounable on JLC's side
    nuxt_script = parser.find('script', text=re.compile('.*__NUXT__.*'))
    nuxt_text = nuxt_script.text
    nuxt_js = js2py.eval_js(nuxt_text)
    try:
        part_num = nuxt_js['data'][0]['presaleTypeTabs'][0]['tableInfo']['tableList'][0]['componentCode']
        return [{'JLCPCB Part Number': part_num}]
    except TypeError:
        return [{'JLCPCB Part Number': ''}]
    # component_table = parser.find('div', {'class': 'el-table__body-wrapper'})
    # component_rows = component_table.find_all('tr', {'class': 'el-table__row'})
    # print(component_rows[0].find('a', {'class': 'item'}))
    # return [_filter_item(row, lambda v: v.search_eval) for row in component_rows]


def get_item(part_number: str) -> dict:
    if len(part_number) == 0:
        # A blank part number is not a valid JLC search
        return {}
    url = f'https://jlcpcb.com/partdetail/{part_number}'
    req = urllib.request.urlopen(url)
    resp = req.read()
    parser = bs4.BeautifulSoup(resp, features='html.parser')
    return _filter_item(parser, lambda v: v.item_eval)


def _filter_item(parser, eval_supplier):
    item = {}
    for field_name, field_value in item_fields.items():
        try:
            item[field_name] = eval(eval_supplier(field_value))
        except (KeyError, IndexError, AttributeError):
            item[field_name] = field_value.default
    return item


if __name__ == "__main__":
    raise NotImplementedError()
# TODO give this file argparse, entrypoint, etc
