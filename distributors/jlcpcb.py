import urllib.request
import bs4


# Fields to be parsed from each JLCPCB item
# Format: (eval_format_string, default_value)
item_fields = {
    'Stock': ('int(parser.find("div", class_="smt-count-component").find("div", class_="text-16").text[len("In Stock: "):])', 0),
    'Manufacturer': ('_item_metavals(parser)[0].text', ''),
    'Manufacturer Part Number': ('_item_metavals(parser)[1].text', ''),
    'Package': ('_item_metavals(parser)[3].text', ''),
    'Description': ('_item_metavals(parser)[4].text', ''),
}


def _item_metavals(parser):
    return parser.find_all("dd", {"data-v-293164dd": True})


def get_item(part_number):
    url = f'https://jlcpcb.com/partdetail/{part_number}'
    req = urllib.request.urlopen(url)
    resp = req.read()
    parser = bs4.BeautifulSoup(resp, features='html.parser')
    item = {}
    for field_name, field_value in item_fields.items():
        try:
            item[field_name] = eval(field_value[0])
        except (KeyError, IndexError, AttributeError):
            item[field_name] = field_value[1]
    return item


if __name__ == "__main__":
    raise NotImplementedError()
#TODO give this file argparse, entrypoint, etc