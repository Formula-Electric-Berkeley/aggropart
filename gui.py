import PySimpleGUI as psg

import bom
import search


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
        key=key
    )


def _make_window():
    rbom_layout = [
        psg.Frame('Remaining BOM', [
            [psg.FileBrowse('Open BOM CSV', enable_events=True, key='-BOM-OPEN-')],
            [rbom_table]
        ])
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
                psg.Combo(values=['Inventory', 'Digikey', 'Mouser', 'JLCPCB'], default_value='Inventory',
                          key='-SEARCH-SRC-'),
                psg.Button(button_text='Search', key='-SEARCH-EXEC-')
            ],
            [ssel_table]
        ])
    ]

    inv_tab = psg.Tab('Inventory', [[inv_table]])
    dk_tab = psg.Tab('Digikey', [[dk_table]])
    mouser_tab = psg.Tab('Mouser', [[mouser_table]])
    jlc_tab = psg.Tab('JLCPCB', [[jlc_table]])

    pbom_layout = [
        psg.Frame('Processed BOM', [
            [psg.Button(button_text='Save BOM')],
            [psg.TabGroup([[inv_tab, dk_tab, mouser_tab, jlc_tab]])]
        ])
    ]

    layout = [rbom_layout, ssel_layout, pbom_layout]

    return psg.Window('aggropart', layout, finalize=True)

if __name__ == "__main__":
    rbom_table = _make_table(bom.altium_fields, '-RBOM-TABLE-')
    ssel_table = _make_table(bom.search_fields, '-SSEL-TABLE-')
    inv_table = _make_table(bom.inv_fields, '-INV-TABLE-')
    dk_table = _make_table(bom.dk_fields, '-DK-TABLE-')
    mouser_table = _make_table(bom.mouser_fields, '-MOUSER-TABLE-')
    jlc_table = _make_table(bom.jlc_fields, '-JLC-TABLE-')

    search_query_input = psg.Input(s=15, tooltip='Query', key='-SEARCH-QUERY-',
                                   disabled=True, disabled_readonly_background_color='#9c9c9c')

    window = _make_window()

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
            search.execute(values['-SEARCH-SRC-'], values['-SEARCH-QUERY-'], rbom_table, ssel_table)
