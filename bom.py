import csv
import os
from pathlib import Path

import common
import inventory
import popups
from distributors import jlcpcbw, digikeyw, mouserw
from digikey.v3.productinformation.models.product_details import ProductDetails


OUT_FOLDER = "out"


#TODO set column sizes dynamically
required_fields = [
    'Comment',
    'Quantity',
    'Digi-Key Part Number',
    'Mouser Part Number',
    'JLCPCB Part Number',
]

optional_fields = [
    'Description',  # For manual review only
    'Designator',  # For manual review only
    # 'Revision Status',    #TODO doesn't work?
    'JLCPCB Part Type'  # Only matters for JLC price esimation
]

bom_fields_msg = f"""
The following BOM fields are required from Altium
{common.pfmt(required_fields)}
The following BOM fields are optional from Altium
{common.pfmt(optional_fields)}
"""

altium_fields = required_fields + optional_fields

inv_fields = list(inventory.db_mappings.keys())

# Get these fields by passing placeholder/invalid items into
# their respective formatter functions, then taking the keys only
dk_fields = list(digikeyw.format_item(ProductDetails()).keys())
mouser_fields = list(mouserw.format_item(mouserw.fake_response_item).keys())
jlc_fields = list(jlcpcbw.item_fields.keys())
_field_maxlen = len(max(inv_fields, dk_fields, mouser_fields, jlc_fields, key=lambda v: len(v)))
search_fields = [f'Placeholder{i}' for i in range(_field_maxlen)]

loaded_filename = str()


def _validate_int(v):
    try:
        _ = int(v)
        return True
    except:
        popups.error('Value entered was not an integer')


def open_(values, rbom_table, pbom_subtables):
    try:
        fp = values['-BOM-OPEN-']
        if not init(fp):
            return
        bom_qty = popups.input_('BOM Quantity: ', default='1', validator=_validate_int)
        if not bom_qty:
            return
        bom_qty = int(bom_qty)

        bom_values = []
        bom_file = read_(fp)
        for item in bom_file:
            bom_item = []
            for field in altium_fields:
                raw_item = item.get(field, str())
                if field == 'Quantity':
                    bom_item.append(int(raw_item) * bom_qty)
                else:
                    bom_item.append(raw_item)
            bom_values.append(bom_item)
        rbom_table.update_values(bom_values)
        for table in pbom_subtables.values():
            table.clear_values()
    except FileNotFoundError:
        popups.error('BOM file not found. Not opening.')
    except ValueError as e:
        popups.error(e)


def init(fp):
    if not os.path.exists(fp):
        popups.error(f"File does not exist: {fp}")
        return False
    elif not fp.lower().endswith('.csv'):
        popups.error(f'Filepath "{fp}" does not end in .csv')
        return False

    global loaded_filename
    loaded_filename = Path(fp).stem
    return True


def read_(fp):
    with open(fp, 'r') as fh:
        bom_csv = csv.reader(fh)
        try:
            headers = next(bom_csv)
        except StopIteration:
            # Check that the header was read - i.e. the file is not already empty
            raise ValueError('BOM did not contain enough data / the data was invalid')

        item_template = {}
        for header in required_fields:
            # Validate that all headers are in the provided BOM
            if header not in headers:
                raise ValueError(f'"{header}" was not found as a header in the BOM')
            # Create a mapping of header name to column index
            item_template[header] = None

        # Not pythonic, but faster
        for header in optional_fields:
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
                try:
                    attribute = row[headers.index(k)]
                    if attribute.isnumeric():
                        attribute = int(attribute)
                    bom_item[k] = attribute
                except ValueError:
                    # Optional missing values get caught here
                    bom_item[k] = -1
        return bom


if __name__ == "__main__":
    raise NotImplementedError()
