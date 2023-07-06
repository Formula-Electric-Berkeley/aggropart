import csv
import os

import inventory
from distributors import jlcpcb, digi_key
from digikey.v3.productinformation.models.product_details import ProductDetails

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

altium_fields = required_fields + optional_fields

inv_fields = list(inventory.db_mappings.keys())
base_dist_fields = [
    'Part Number',
    'Quantity',
    'Description'
]
dk_fields = list(digi_key.format_item(ProductDetails()).keys())
mouser_fields = base_dist_fields
jlc_fields = base_dist_fields + list(jlcpcb.item_fields.keys())
_field_maxlen = len(max(inv_fields, dk_fields, mouser_fields, jlc_fields, key=lambda v: len(v)))
search_fields = [f'Placeholder{i}' for i in range(_field_maxlen)]


def init(fp):
    if not os.path.exists(fp):
        raise FileNotFoundError(fp)

    if not fp.lower().endswith('.csv'):
        raise ValueError(f'Filepath "{fp}" does not end in .csv')

    os.makedirs('out/', exist_ok=True)


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
                attribute = row[headers.index(k)]
                if attribute.isnumeric():
                    attribute = int(attribute)
                bom_item[k] = attribute
        return bom

if __name__ == "__main__":
    raise NotImplementedError()
