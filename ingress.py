#!/usr/bin/env python3
"""
Automatically queries, inventories, and labels items purchased from Digikey and Mouser.
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from pystrich.datamatrix import DataMatrixEncoder
import segno

import common
import inventory
from distributors import digikeyw, mouserw


PX_PER_IN = 203 #8 DPI
LABEL_W_PX = int(PX_PER_IN * 2.25)
LABEL_H_PX = PX_PER_IN * 4
CODE_CELL_SIZE = 20
LABEL_FONT_SIZE = 40
FONT_REL_PATH = 'Consolas.ttf'
QR_IMG_FN = 'qr.png'
DM_IMG_FN = 'dm.png'
LABEL_PDF_FN = 'labels.pdf'


def main(args):
    # Get items from distributor corresponding to passed argument
    order_items = mouserw.get_order_items(args.order) if args.distributor == 'mouser' else digikeyw.get_order_items(args.order)
    order_items_std = [DistributorItem(args.distributor, item) for item in order_items]
    if len(order_items_std) == 0:
        print(f'No items were retrieved from the supplied {args.distributor} order ID {args.order}')

    # Query the EECS Box inventory, map names to page IDs, and filter out the qualifying words
    box_inv_raw = inventory.get_db(db_id=os.environ['NOTION_BOX_DB_ID'])
    box_inv = {inventory._filter_inv_item(item, inventory.db_mappings['Part Number']).replace("EECS Box ", ""): item['id'] for item in box_inv_raw}

    labels = []
    for item in order_items_std:
        common.pprint(item.to_dict())
        resp = None
        while True:
            # Keep trying until a valid box is entered
            resp = input('Which EECS Box should this go into? (ex XS0099, S0099, M0099 - leave blank to skip)? ')
            if resp in box_inv:
                break
            else:
                print(f'Box {resp} not in EECS inventory. Please try again.')

        # Process the item only if there was no user input
        if len(resp) != 0:
            props = make_props(item, box_inv[resp])
            notion_page = inventory.insert_db(properties=props)

            # Make data matrix and QR images, then save to temporary files
            dm = DataMatrixEncoder(notion_page['url'])
            dm.save(DM_IMG_FN, cellsize=CODE_CELL_SIZE)

            qr = segno.make_qr(notion_page['url'], error='H')
            qr.save(QR_IMG_FN, scale=CODE_CELL_SIZE)

            # Reopen data matrix and QR images and scale to label size
            dm_img = open_and_scale_img(DM_IMG_FN, 0.35, True)
            qr_img = open_and_scale_img(QR_IMG_FN, 0.45, True)

            # Paste data matrix, QR, part number text onto label
            label = ImageBuilder()
            label.append_blank(15)
            label.append_img(dm_img)
            label.append_img(qr_img)
            label.append_blank(15)
            label.append_text(item.mfg_part_num)
            labels.append(label.dst)

            # Delete temporary data matrix and QR images
            os.remove(QR_IMG_FN)
            os.remove(DM_IMG_FN)

    # Save all the label images to a single PDF (considers 0 and 1 label edge cases)
    if len(labels) > 1:
        labels[0].save(LABEL_PDF_FN, save_all=True, append_images=labels[1:])
    elif len(labels) > 0:
        labels[0].save(LABEL_PDF_FN)

class DistributorItem:
    def __init__(self, distributor_name, item):
        """Represents an order (part) item from a distributor. Standardized set of properties."""
        self.distributor = distributor_name
        if distributor_name == 'digikey':
            self._digikey_fmt(item)
        elif distributor_name == 'mouser':
            self._mouser_fmt(item)
        else:
            raise ValueError(f'Invalid distributor name: {distributor_name}')

    def _digikey_fmt(self, item):
        self.mfg_part_num = item.manufacturer_part_number
        self.dist_part_num = item.digi_key_part_number
        self.description = item.product_description
        self.qty = item.quantity
        self.unit_price = item.unit_price
        self.total_price = item.total_price

    def _mouser_fmt(self, item):
        self.mfg_part_num = item['ProductInfo']['ManufacturerPartNumber']
        self.dist_part_num = item['ProductInfo']['MouserPartNumber']
        self.description = item['ProductInfo']['PartDescription']
        self.qty = item['Quantity']
        self.unit_price = item['UnitPrice']
        self.total_price = item['ExtPrice']

    def to_dict(self):
        """Format the distributor item as a dictionary."""
        return {
            'Mfg Part Number': self.mfg_part_num,
            f'{self.distributor.title()} Part Number': self.dist_part_num,
            'Description': self.description,
            'Quantity': self.qty,
            'Unit Price': self.unit_price,
            'Total Price': self.total_price,
        }


def make_props(item, box_id):
    """Create a properties dict according to the Notion inventory schema."""
    return {
        'Part Number': {
            "id": "title",
            "type": "title",
            "title": [
                make_rich_text_prop(item.mfg_part_num)
            ]
        },
        'Current Quantity': {
            "number": item.qty,
        },
        'Description': {
            "rich_text": [
                make_rich_text_prop(item.description)
            ]
        },
        'Box': {
            "relation": [{ "id": box_id }]
        }
    }


def make_rich_text_prop(text):
    """Create a single rich text type property for Notion inventory insertion."""
    return {
        "type": "text",
        "text": {
            "content": text,
            "link": None
        },
        "annotations": {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default"
        },
        "plain_text": text,
        "href": None
    }


class ImageBuilder:
    _font = ImageFont.truetype(FONT_REL_PATH, LABEL_FONT_SIZE)

    def __init__(self):
        """Builds an image by stacking existing images (and text) horizontally. Grayscale with white background."""
        self.dst = Image.new('L', (LABEL_W_PX, LABEL_H_PX), 'WHITE')
        self.last_y = 0

    def append_img(self, img):
        """Append a PIL grayscale image onto the bottom of the current image stack."""
        self.dst.paste(img, ((LABEL_W_PX - img.width) // 2, self.last_y))
        self.last_y += img.height

    def append_text(self, msg):
        """Append a text string onto the bottom of the current image stack."""
        draw = ImageDraw.Draw(self.dst)
        _, _, text_width, text_height = draw.textbbox((0, 0), msg, font=ImageBuilder._font)
        if text_width > LABEL_W_PX:
            # Text is too big for label; split into two hstacked lines of text
            cutoff_idx = len(msg) // 2
            self.append_text(msg[:cutoff_idx])
            self.append_blank(LABEL_FONT_SIZE // 2)
            self.append_text(msg[cutoff_idx:])
        else:
            # Draw text normally; width centered and appended to the bottom
            draw.text(((LABEL_W_PX - text_width) // 2, self.last_y + (text_height // 2)), msg, font=ImageBuilder._font)
            self.last_y += text_height

    def append_blank(self, px):
        """Append a blank space onto the bottom of the current image stack. Does not do any drawing."""
        self.last_y += px

    def save(self, fn):
        """Save the current image stack output to a file."""
        self.dst.save(fn)


def open_and_scale_img(fn, scale, scale_is_height):
    """Open an image at filepath fn using PIL, then scale either height or width as a proportion of label height/width."""
    img = Image.open(fn)
    if scale_is_height:
        y = LABEL_H_PX * scale
        x = (y / img.height) * img.width
    else:
        x = LABEL_W_PX * scale
        y = (x / img.width) * img.height
    return img.resize((int(x), int(y)))


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('order', help='Digikey SALES order ID or Mouser SALES order number (not web/invoice)')
    distributors = parser.add_subparsers(dest='distributor', help='distributor source for the passed sales order number', required=True)

    dist_digikey = distributors.add_parser('digikey')
    dist_digikey.add_argument('--id', '-i', help='Digikey client ID; required if not specified in .env')
    dist_digikey.add_argument('--secret', '-s', help='Digikey client secret; required if not specified in .env')

    dist_mouser = distributors.add_parser('mouser')
    dist_mouser.add_argument('--key', '-k', help='Mouser API key; required if not specified in .env')

    args = parser.parse_args()

    if args.distributor == 'digikey':
        common.checkset_env('DIGIKEY_CLIENT_ID', args.id, 'Digikey client ID')
        common.checkset_env('DIGIKEY_CLIENT_SECRET', args.secret, 'Digikey client secret')
    elif args.distributor == 'mouser':
        common.checkset_env('MOUSER_API_KEY', args.key, 'Mouser API key')

    return main(args)


if __name__ == "__main__":
    common.init_dotenv()
    sys.exit(_parse_args())
