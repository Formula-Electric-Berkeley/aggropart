import csv
import os

import common
import inventory
import popups
from distributors import jlcpcbw, digikeyw, mouserw
from digikey.v3.productinformation.models.product_details import ProductDetails


OUT_FOLDER = "out"


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


def init(fp):
    if not os.path.exists(fp):
        popups.error(f"File does not exist: {fp}")
    elif not fp.lower().endswith('.csv'):
        popups.error(f'Filepath "{fp}" does not end in .csv')


def read(fp):
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
