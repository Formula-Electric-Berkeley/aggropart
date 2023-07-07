import bom
import inventory

from distributors import digikeyw, mouserw, jlcpcbw

class PartSearcher:
    def __init__(self, rbom_table, ssel_table):
        self.rbom_table = rbom_table
        self.ssel_table = ssel_table

    def execute(self, src, query):
        if src == 'Inventory':
            self._search_inv(query)
        elif src == 'Digikey':
            self._search_dk(query)
        elif src == 'Mouser':
            self._search_mouser(query)
        elif src == 'JLCPCB':
            self._search_jlc(query)

    def _get_selected_rbom_row(self):
        if len(self.rbom_table.SelectedRows) == 0:
            return None
        else:
            sel_table_row = self.rbom_table.Values[self.rbom_table.SelectedRows[0]]
            return {k: sel_table_row[i] for i, k in enumerate(bom.altium_fields)}

    def _update_gui(self, values, headings):
        self.ssel_table.update(values=values)
        padded_headings = headings + [''] * (len(bom.search_fields) - len(headings))
        for cid, text in zip(bom.search_fields, padded_headings):
            self.ssel_table.Widget.heading(cid, text=text)

    def _search_inv(self, query):
        inv = inventory.list_db(inventory.get_db())
        if query:
            found_items = _search_inv_by_query(query, inv)
        else:
            sel_row = self._get_selected_rbom_row()
            found_items = _search_inv_by_item(sel_row, inv) if sel_row else \
                [_inv_item_unmap(inv_item) for inv_item in inv]
        self._update_gui(found_items, bom.inv_fields)

    def _search_dk(self, query):
        if query:
            dk_resp = digikeyw.search_items(query)
            fmt_dk_items = [list(digikeyw.format_item(item).values()) for item in dk_resp.products]
            self._update_gui(fmt_dk_items, bom.dk_fields)
        else:
            sel_row = self._get_selected_rbom_row()
            dk_pn = sel_row['Digi-Key Part Number']
            dk_item = digikeyw.get_item(dk_pn)
            fmt_dk_item = digikeyw.format_item(dk_item)
            self._update_gui([list(fmt_dk_item.values())], bom.dk_fields)

    def _search_mouser(self, query):
        if query:
            mouser_resp = mouserw.search_items(query)
            fmt_mouser_items = [list(mouserw.format_item(item).values()) for item in mouser_resp]
            self._update_gui(fmt_mouser_items, bom.mouser_fields)
        else:
            sel_row = self._get_selected_rbom_row()
            mouser_pn = sel_row['Mouser Part Number']
            mouser_item = mouserw.get_item(mouser_pn)
            fmt_mouser_item = mouserw.format_item(mouser_item)
            self._update_gui([list(fmt_mouser_item.values())], bom.mouser_fields)

    def _search_jlc(self, query):
        if query:
            #TODO fix
            pass
        else:
            sel_row = self._get_selected_rbom_row()
            jlc_pn = sel_row['JLCPCB Part Number']
            jlc_item = jlcpcbw.get_item(jlc_pn)
            fmt_jlc_item = [list(jlc_item.values())]
            self._update_gui(fmt_jlc_item, bom.jlc_fields)


def _search_inv_by_query(query, inv):
    found_items = []
    if type(query) != str:
        return []
    if len(query) == 0:
        return inv

    for inv_item in inv:
        for inv_attr_val in inv_item.values():
            if type(inv_attr_val) == str and len(inv_attr_val) > 0 and \
                    (query in inv_attr_val or inv_attr_val in query):
                found_items.append(_inv_item_unmap(inv_item))
    return found_items


def _search_inv_by_item(item, inv):
    found_items = []
    if item is None:
        return []
    for inv_item in inv:
        if _has_matching_properties(item, inv_item) and \
                (inv_item['Quantity'] >= item['Quantity']):
            found_items.append(_inv_item_unmap(inv_item))
    return found_items


def _has_matching_properties(sel_item: dict[str], inv_item: dict) -> bool:
    for sel_attr_val in sel_item.values():
        for inv_attr_val in inv_item.values():
            if type(sel_attr_val) == str and type(inv_attr_val) == str and \
                    len(sel_attr_val) > 0 and len(inv_attr_val) > 0 and \
                    (sel_attr_val in inv_attr_val or inv_attr_val in sel_attr_val):
                return True
    return False


def _inv_item_unmap(item):
    return [item[k] for k in bom.inv_fields]


if __name__ == "__main__":
    raise NotImplementedError()
