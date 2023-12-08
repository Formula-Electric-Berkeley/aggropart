#!/usr/bin/env python3
"""
TODO add description
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from pystrich.datamatrix import DataMatrixEncoder
import segno

import common
import inventory
from distributors import digikeyw


PX_PER_IN = 203 #8 DPI
LABEL_W_PX = int(PX_PER_IN * 2.25)
LABEL_H_PX = PX_PER_IN * 4
CODE_CELL_SIZE = 20
LABEL_FONT_SIZE = 40
FONT_REL_PATH = 'Consolas.ttf'
QR_IMG_FN = 'qr.png'
DM_IMG_FN = 'dm.png'


def main(args):
    order_items = digikeyw.get_order_items(args.order)[:2]
    labels = []
    for item in order_items:
        common.pprint(format_order_item(item))
        if (common.wait_yn('Enter item into Notion and print label?')):
            props = {
                'Part Number': inventory.make_text_property(item.manufacturer_part_number),
                'Current Quantity': item.quantity,
                'Description': inventory.make_text_property(item.product_description),
                # 'EECS Box': 'S0019'
            }
            notion_page = inventory.insert_db(props)

            qr = segno.make_qr(notion_page['url'], error='H')
            qr.save(QR_IMG_FN, scale=CODE_CELL_SIZE)

            dm = DataMatrixEncoder(notion_page['url'])
            dm.save(DM_IMG_FN, cellsize=CODE_CELL_SIZE)

            qr_img = open_and_scale_img(QR_IMG_FN, 0.45, True)
            dm_img = open_and_scale_img(DM_IMG_FN, 0.35, True)

            label = ImageBuilder()
            label.append_img(qr_img)
            label.append_img(dm_img)
            label.append_blank(20)
            label.append_text(item.manufacturer_part_number)
            label.save(f"temp/{item.manufacturer_part_number}.png")
            labels.append(label.dst)

            os.remove(QR_IMG_FN)
            os.remove(DM_IMG_FN)

    labels[0].save('labels.pdf', save_all=True, append_images=labels[1:])
            

def format_order_item(item):
    return {
        'Mfg Part Number': item.manufacturer_part_number,
        'Digikey Part Number': item.digi_key_part_number,
        'Description': item.product_description,
        'Quantity': item.quantity,
        'Unit Price': item.unit_price,
        'Total Price': item.total_price,
    }


class ImageBuilder:
    _font = ImageFont.truetype(FONT_REL_PATH, LABEL_FONT_SIZE)

    def __init__(self):
        self.dst = Image.new('L', (LABEL_W_PX, LABEL_H_PX), 'WHITE')
        self.last_y = 0

    def append_img(self, img):
        self.dst.paste(img, ((LABEL_W_PX - img.width) // 2, self.last_y))
        self.last_y += img.height

    def append_text(self, msg):
        draw = ImageDraw.Draw(self.dst)
        _, _, text_width, text_height = draw.textbbox((0, 0), msg, font=ImageBuilder._font)
        if text_width > LABEL_W_PX:
            cutoff_idx = len(msg) // 2
            self.append_text(msg[:cutoff_idx])
            self.append_blank(LABEL_FONT_SIZE // 2)
            self.append_text(msg[cutoff_idx:])
        else:
            draw.text(((LABEL_W_PX - text_width) // 2, self.last_y + (text_height // 2)), msg, font=ImageBuilder._font)
            self.last_y += text_height

    def append_blank(self, px):
        self.last_y += px

    def save(self, fn):
        self.dst.save(fn)


def open_and_scale_img(fn, scale, scale_is_height):
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
    parser.add_argument('order', help='Digikey sales order ID')
    parser.add_argument('--id', '-i', help='Digikey client ID; required if not specified in .env')
    parser.add_argument('--secret', '-s', help='Digikey client secret; required if not specified in .env')
    args = parser.parse_args()

    common._checkset_env('DIGIKEY_CLIENT_ID', args.id, 'Digikey client ID')
    common._checkset_env('DIGIKEY_CLIENT_SECRET', args.secret, 'Digikey client secret')

    return main(args)


if __name__ == "__main__":
    common.init_dotenv()
    sys.exit(_parse_args())


#read digikey and mouser invoices
# add items to inventory (prompt for box)
# print label
# minimize number of clicks