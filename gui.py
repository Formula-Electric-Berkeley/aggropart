#!/usr/bin/env python3
"""
TODO add description
"""

import dotenv
import PySimpleGUI as psg

import bom
import partsearcher

bom_file = None


def _open_bom_file(fp):
    bom.init(fp)
    global bom_file
    bom_file = bom.read(fp)
    bom_values = [[item[k] for k in bom.altium_fields] for item in bom_file]
    rbom_table.update(values=bom_values)


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
                psg.Button(button_text='Search', key='-SEARCH-EXEC-')
            ],
            [ssel_table]
        ], key='-SSEL-FRAME-')
    ]

    inv_tab = psg.Tab('Inventory', [[inv_table]])
    dk_tab = psg.Tab('Digikey', [[dk_table]])
    mouser_tab = psg.Tab('Mouser', [[mouser_table]])
    jlc_tab = psg.Tab('JLCPCB', [[jlc_table]])

    pbom_layout = [
        psg.Frame('Processed BOM', [
            [
                # TODO make these buttons do things
                psg.Button(button_text='Export Current PBOM'),
                psg.Button(button_text='Export All PBOMs'),
                psg.Push(),
                psg.Button(button_text='↓ Associate Item With Part ↓'),
                psg.Button(button_text='↑ Remove Item From Part ↑'),
            ],
            [psg.TabGroup([[inv_tab, dk_tab, mouser_tab, jlc_tab]])]
        ], key='-PBOM-FRAME-')
    ]

    file_opts = ['Export Current PBOM', 'Export All PBOMs', 'Clear Inventory Cache', 'Clear All Tables']
    help_opts = ['Instructions', 'Required BOM Fields', 'About aggropart']
    # TODO make these buttons do things
    menu = [psg.Menu([['File', file_opts], ['Help', help_opts]], key='-MENUBAR-', p=0)]

    layout = [menu, rbom_layout, ssel_layout, pbom_layout]

    return psg.Window('aggropart', layout, finalize=True, size=(800, 750))


def _pack_frame(name):
    window[name].Widget.pack_propagate(0)
    window[name].Widget.config(
        width=window.size[0], height=window.size[1] // 3
    )


if __name__ == "__main__":
    dotenv.load_dotenv()

    rbom_table = _make_table(bom.altium_fields, '-RBOM-TABLE-')
    ssel_table = _make_table(bom.search_fields, '-SSEL-TABLE-')
    inv_table = _make_table(bom.inv_fields, '-INV-TABLE-')
    dk_table = _make_table(bom.dk_fields, '-DK-TABLE-')
    mouser_table = _make_table(bom.mouser_fields, '-MOUSER-TABLE-')
    jlc_table = _make_table(bom.jlc_fields, '-JLC-TABLE-')

    search_query_input = psg.Input(s=15, tooltip='Query', key='-SEARCH-QUERY-',
                                   disabled=True, disabled_readonly_background_color='#9c9c9c')

    window = _make_window()
    _pack_frame('-RBOM-FRAME-')
    _pack_frame('-SSEL-FRAME-')
    _pack_frame('-PBOM-FRAME-')

    searcher = partsearcher.PartSearcher(rbom_table, ssel_table)

    while True:
        event, values = window.read()
        print(event, values)
        if event == psg.WIN_CLOSED or event == 'Exit':
            break
        elif event == '-BOM-OPEN-':
            try:
                _open_bom_file(values['-BOM-OPEN-'])
            except FileNotFoundError:
                psg.Popup('BOM file not found. Not opening.')
            except ValueError as e:
                psg.Popup(e)
        elif event == '-SELECT-SEARCH-QUERY-':
            search_query_input.update(disabled=False)
        elif event == '-SELECT-SEARCH-PART-':
            search_query_input.update(disabled=True, value='')
        elif event == '-SEARCH-EXEC-':
            searcher.execute(values['-SEARCH-SRC-'], values['-SEARCH-QUERY-'])
