#!/usr/bin/env python3
"""
TODO add description
"""

import csv

import PySimpleGUI as psg

import bom
import common
import inventory
import partsearcher
import popups


_event_registry = {}
_current_tab = 'Inventory'


def _register_event(event_name, func):
    _event_registry[event_name] = func


def _register_all_events():
    _register_event('-BOM-OPEN-', _open_bom)
    _register_event('-SELECT-SEARCH-QUERY-', lambda: search_query_input.update(disabled=False))
    _register_event('-SELECT-SEARCH-PART-', lambda: search_query_input.update(disabled=True, value=''))
    _register_event('-SEARCH-EXEC-', lambda: searcher.execute(values['-SEARCH-SRC-'], values['-SEARCH-QUERY-']))
    _register_event('-PBOM-TAB-SWITCH-', _set_current_tab)
    _register_event('-ASSOC-ITEM-PART-', _assoc_item_part)
    _register_event('-RM-ITEM-PART-', _rm_item_part)

    _register_event('Instructions', lambda: popups.info(popups.instructions_msg))
    _register_event('Required BOM Fields', lambda: popups.info(popups.bom_fields_msg))
    _register_event('About aggropart', lambda: popups.info(popups.about_msg))
    # TODO fix these
    _register_event('Export Current PBOM', lambda: _export_pbom(_current_tab))
    _register_event('-EXPORT-C-PBOM-', lambda: _export_pbom(_current_tab))
    _register_event('Export All PBOMs', _export_all_pboms)
    _register_event('-EXPORT-A-PBOM-', _export_all_pboms)
    _register_event('Clear Inventory Cache', inventory.clear_caches)
    _register_event('Clear All Tables', _clear_tables)


def _open_bom():
    try:
        fp = values['-BOM-OPEN-']
        bom.init(fp)
        bom_file = bom.read(fp)
        bom_values = [[item.get(k, str()) for k in bom.altium_fields] for item in bom_file]
        rbom_table.update(values=bom_values)
    except FileNotFoundError:
        popups.error('BOM file not found. Not opening.')
    except ValueError as e:
        popups.error(e)


def _export_pbom(src):
    table = pbom_subtables[src]
    with open(f'out/{src.lower()}_bom.csv', 'w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(bom.altium_fields + [''] + table.ColumnHeadings)
        for part, item in zip(item_part_assoc_map[src], table.Values):
            writer.writerow(part + [''] + item)


def _export_all_pboms():
    for src in pbom_subtables.keys():
        _export_pbom(src)


def _assoc_item_part():
    rbom_row = get_selected_table_row(rbom_table, fmt=False)
    ssel_row = get_selected_table_row(ssel_table, fmt=False)
    if not rbom_row:
        popups.error('No Remaining BOM row selected / row is invalid')
        return
    if not ssel_row:
        popups.error('No Source Selector row selected / row is invalid')
        return
    if not searcher.last_src or searcher.last_src not in pbom_subtables:
        popups.error('Search was never performed')
        return

    pbom_table = pbom_subtables[searcher.last_src]
    new_rbom_values = rbom_table.Values
    new_rbom_values.pop(rbom_table.SelectedRows[0])
    rbom_table.update(values=new_rbom_values)

    new_pbom_values = pbom_table.Values
    new_pbom_values.append(ssel_row)
    pbom_table.update(values=new_pbom_values)

    item_part_assoc_map[searcher.last_src].append(rbom_row)


def _set_current_tab():
    global _current_tab
    _current_tab = values['-PBOM-TAB-SWITCH-']


def _rm_item_part():
    pbom_table = pbom_subtables[_current_tab]
    pbom_row = get_selected_table_row(pbom_table, fmt=False)
    if not pbom_row:
        popups.error('No Processed BOM row selected / row is invalid')
        return

    new_pbom_values = pbom_table.Values
    sel_idx = pbom_table.SelectedRows[0]
    new_pbom_values.pop(sel_idx)
    pbom_table.update(values=new_pbom_values)

    new_rbom_values = rbom_table.Values
    new_rbom_values.append(item_part_assoc_map[_current_tab][sel_idx])
    rbom_table.update(values=new_rbom_values)


def get_selected_table_row(table, fmt=True):
    if len(table.SelectedRows) == 0:
        return None
    else:
        sel_table_row = table.Values[table.SelectedRows[0]]
        return {k: sel_table_row[i] for i, k in enumerate(table.ColumnHeadings)} if fmt else sel_table_row


def _clear_tables():
    rbom_table.update(values=[])
    ssel_table.update(values=[])
    for table in pbom_subtables.values():
        table.update(values=[])


def _make_table(headings, key):
    return psg.Table(
        headings=headings,
        values=[],
        col_widths=[len(item) for item in headings],
        auto_size_columns=False,
        key=key,
        hide_vertical_scroll=False,
        vertical_scroll_only=False
    )


def _make_table_tab(src):
    return psg.Tab(src, [[pbom_subtables[src]]])


def _make_window():
    rbom_layout = [
        psg.Frame('Remaining BOM', [
            [psg.FileBrowse('Open BOM CSV', enable_events=True, key='-BOM-OPEN-')],
            [rbom_table]
        ], key='-RBOM-FRAME-')
    ]

    ssel_layout = [
        psg.Frame('Source Selector', [
            [
                psg.Text('Search by: '),
                psg.Radio(text='Selected Part', group_id='search', default=True,
                          key='-SELECT-SEARCH-PART-', enable_events=True),
                psg.Radio(text='Query', group_id='search', key='-SELECT-SEARCH-QUERY-', enable_events=True),
                search_query_input,
                psg.Text(text='Search from: '),
                psg.OptionMenu(values=['Inventory', 'Digikey', 'Mouser', 'JLCPCB'], default_value='Inventory',
                               key='-SEARCH-SRC-'),
                psg.Button(button_text='Search', key='-SEARCH-EXEC-'),
            ],
            [ssel_table]
        ], key='-SSEL-FRAME-')
    ]

    pbom_layout = [
        psg.Frame('Processed BOM', [
            [
                psg.Button(button_text='Export Current PBOM', key='-EXPORT-C-PBOM-'),
                psg.Button(button_text='Export All PBOMs', key='-EXPORT-A-PBOM-'),
                psg.Push(),
                psg.Button(button_text='↓ Associate Item With Part ↓', key='-ASSOC-ITEM-PART-'),
                psg.Button(button_text='↑ Remove Item From Part ↑', key='-RM-ITEM-PART-'),
            ],
            [psg.TabGroup([[
                _make_table_tab('Inventory'),
                _make_table_tab('Digikey'),
                _make_table_tab('Mouser'),
                _make_table_tab('JLCPCB')]],
                enable_events=True,
                key='-PBOM-TAB-SWITCH-'
            )]
        ], key='-PBOM-FRAME-')
    ]

    file_opts = ['Export Current PBOM', 'Export All PBOMs', 'Clear Inventory Cache', 'Clear All Tables']
    help_opts = ['Instructions', 'Required BOM Fields', 'About aggropart']
    menu = [psg.Menu([['File', file_opts], ['Help', help_opts]], key='-MENUBAR-', p=0)]

    layout = [menu, rbom_layout, ssel_layout, pbom_layout]

    with open('images/logo.png', 'rb') as f:
        psg.set_global_icon(f.read())

    return psg.Window('aggropart', layout, finalize=True, size=(800, 750))


def _pack_frame(name):
    window[name].Widget.pack_propagate(0)
    window[name].Widget.config(
        width=window.size[0],
        height=window.size[1] // 3
    )


if __name__ == "__main__":
    common.init_dotenv()

    rbom_table = _make_table(bom.altium_fields, '-RBOM-TABLE-')
    ssel_table = _make_table(bom.search_fields, '-SSEL-TABLE-')
    pbom_subtables = {
        'Inventory': _make_table(bom.inv_fields, '-INV-TABLE-'),
        'Digikey': _make_table(bom.dk_fields, '-DK-TABLE-'),
        'Mouser': _make_table(bom.mouser_fields, '-MOUSER-TABLE-'),
        'JLCPCB': _make_table(bom.jlc_fields, '-JLC-TABLE-')
    }
    item_part_assoc_map = {k: [] for k in pbom_subtables.keys()}

    search_query_input = psg.Input(s=15, tooltip='Query', key='-SEARCH-QUERY-',
                                   disabled=True, disabled_readonly_background_color='#9c9c9c')

    window = _make_window()
    _pack_frame('-RBOM-FRAME-')
    _pack_frame('-SSEL-FRAME-')
    _pack_frame('-PBOM-FRAME-')

    searcher = partsearcher.PartSearcher(rbom_table, ssel_table)

    _register_all_events()

    while True:
        event, values = window.read()
        print(event, values)
        if event == psg.WIN_CLOSED or event == 'Exit':
            break

        for r_event, r_func in _event_registry.items():
            if event == r_event:
                r_func()
                break
