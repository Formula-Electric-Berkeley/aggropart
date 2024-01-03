import os
import threading

import bom
import gui
import inventory
import popups

from distributors import digikeyw, mouserw, jlcpcbw


class PartSearcher:
    def __init__(self, window, rbom_table, ssel_table):
        self.window = window
        self.rbom_table = rbom_table
        self.ssel_table = ssel_table
        self.last_src = None
        self.update_queue = []

    def execute(self, src, query):
        self.last_src = src
        if src == 'Inventory':
            if _check_missing_env('NOTION_TOKEN', src) or _check_missing_env('NOTION_INV_DB_ID', src):
                return
            self.window.write_event_value('-INV-UPDATE-BEGIN-', None)
            inv_thread = threading.Thread(target=self._search_inv, args=(query,))
            inv_thread.daemon = True
            inv_thread.start()
        elif src == 'Digikey':
            if _check_missing_env('DIGIKEY_CLIENT_ID', src) or \
                    _check_missing_env('DIGIKEY_CLIENT_SECRET', src) or \
                    _check_missing_env('DIGIKEY_STORAGE_PATH', src):
                return
            self._search_dk(query)
        elif src == 'Mouser':
            if _check_missing_env('MOUSER_PART_API_KEY', src):
                return
            self._search_mouser(query)
        elif src == 'JLCPCB':
            self._search_jlc(query)

    def _update_gui(self, values, headings):
        self.ssel_table.update_values(values)
        padded_headings = headings + [''] * (len(bom.search_fields) - len(headings))
        for cid, text in zip(bom.search_fields, padded_headings):
            self.ssel_table.Widget.heading(cid, text=text)

    def update_gui_queued(self):
        if len(self.update_queue) > 0:
            values = self.update_queue.pop()
            self._update_gui(values, bom.inv_fields)
            self.window.write_event_value('-INV-UPDATE-END-', None)

    def _search_inv(self, query):
        query = query.lower()
        inv = inventory.list_db(inventory.get_db())
        if query:
            found_items = _search_inv_by_query(query, inv)
        else:
            sel_row = self.rbom_table.get_selected_row()
            found_items = _search_inv_by_item(sel_row, inv) if sel_row else \
                [_inv_item_unmap(inv_item) for inv_item in inv]
        self.update_queue.append(found_items)
        self.window.write_event_value('-INV-UPDATE-QUEUED-', None)

    def _search_dk(self, query):
        self._generic_search(query, 'Digi-Key Part Number',
                             digikeyw.get_item, digikeyw.search_items, digikeyw.format_item,
                             bom.dk_fields)

    def _search_mouser(self, query):
        self._generic_search(query, 'Mouser Part Number',
                             mouserw.get_item, mouserw.search_items, mouserw.format_item,
                             bom.mouser_fields)

    def _search_jlc(self, query):
        self._generic_search(query, 'JLCPCB Part Number',
                             jlcpcbw.get_item, jlcpcbw.search_items, None,
                             bom.jlc_fields)

    def _generic_search(self, query, row_key, get_item_func, search_func, fmt_func, fields):
        if query:
            resp = search_func(query)
            fmt_items = [list((fmt_func(item) if fmt_func else item).values()) for item in resp]
            self._update_gui(fmt_items, fields)
        else:
            sel_row = self.rbom_table.get_selected_row()
            if not sel_row:
                popups.error('No RBOM row was selected')
                return
            part_number = sel_row[row_key]
            item = get_item_func(part_number)
            fmt_item = fmt_func(item) if fmt_func else item
            self._update_gui([list(fmt_item.values())], fields)


def _search_inv_by_query(query, inv):
    found_items = []
    if type(query) != str:
        return []
    if len(query) == 0:
        return inv

    for inv_item in inv:
        for inv_attr_val in inv_item.values():
            if type(inv_attr_val) != str:
                continue
            inv_attr_val = inv_attr_val.lower()
            if len(inv_attr_val) > 0 and (query in inv_attr_val or inv_attr_val in query):
                found_item = _inv_item_unmap(inv_item)
                if found_item not in found_items:
                    found_items.append(found_item)
    return found_items


def _search_inv_by_item(item, inv):
    found_items = []
    if item is None:
        return []
    for inv_item in inv:
        if _has_matching_properties(item, inv_item) and \
                (inv_item['Quantity'] >= item['Quantity']):
            found_item = _inv_item_unmap(inv_item)
            if found_item not in found_items:
                found_items.append(found_item)
    return found_items


def _has_matching_properties(sel_item: dict, inv_item: dict) -> bool:
    for sel_attr_val in sel_item.values():
        for inv_attr_val in inv_item.values():
            if type(sel_attr_val) != str or type(inv_attr_val) != str:
                continue
            inv_attr_val = inv_attr_val.lower()
            sel_attr_val = sel_attr_val.lower()
            if len(sel_attr_val) > 0 and len(inv_attr_val) > 0 and \
                    (sel_attr_val in inv_attr_val or inv_attr_val in sel_attr_val):
                return True
    return False


def _inv_item_unmap(item):
    return [item[k] for k in bom.inv_fields]


def _check_missing_env(key, designator):
    key_missing = key not in os.environ or len(os.environ[key]) == 0
    if key_missing:
        popups.error(f'No {key} environment variable. Not searching {designator}.')
    return key_missing


if __name__ == "__main__":
    raise NotImplementedError()
