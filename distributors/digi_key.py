#!/usr/bin/env python3
"""
TODO add description
"""

import digikey as dk_api

from digikey.v3.productinformation import KeywordSearchRequest

def search_items(keyword, max_items=10):
    request = KeywordSearchRequest(keywords=keyword, record_count=max_items)
    return dk_api.keyword_search(body=request)

def get_item(part_number):
    return dk_api.product_details(part_number)

def format_item(item):
    return {
        'Part Number': item.manufacturer_part_number,
        'Description': item.product_description,
        'Quantity Available': item.quantity_available,
        'Minimum Order Quantity': item.minimum_order_quantity,
        'Marketplace': item.marketplace,
        'Non-stock': item.non_stock,
        'Obsolete': item.obsolete,
        'Product Status': item.product_status,
        'Unit Price': item.unit_price,
        'Datasheet URL': item.primary_datasheet,
        'Digikey URL': item.product_url,
    }