import bom
import inventory

from distributors import digi_key, mouser, jlcpcb

def execute(src, query, rbom_table, ssel_table):
    if src == 'Inventory':
        _search_inv(query, rbom_table, ssel_table)
    elif src == 'Digikey':
        _search_dk(query, rbom_table, ssel_table)
    elif src == 'Mouser':
        pass
    elif src == 'JLCPCB':
        pass

def _get_selected_rbom_row(rbom_table):
    if len(rbom_table.SelectedRows) == 0:
        return None
    else:
        sel_table_row = rbom_table.Values[rbom_table.SelectedRows[0]]
        return {k: sel_table_row[i] for i, k in enumerate(bom.altium_fields)}

def _search_inv(query, rbom_table, ssel_table):
    inv = inventory.list_db(inventory.get_db())
    if query:
        found_items = _search_inv_by_query(query, inv)
    else:
        sel_row = _get_selected_rbom_row(rbom_table)
        found_items = _search_inv_by_item(sel_row, inv) if sel_row else \
            [_inv_item_unmap(inv_item) for inv_item in inv]
    ssel_table.update(values=found_items)
    inv_fields = bom.inv_fields + [''] * (len(bom.search_fields) - len(bom.inv_fields))
    for cid, text in zip(bom.search_fields, inv_fields):
        ssel_table.Widget.heading(cid, text=text)


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


def _search_dk(query, rbom_table, ssel_table):
    if query:
        digi_key.search_items(query)
    else:
        digi_key.get_item()

if __name__ == "__main__":
    raise NotImplementedError()
