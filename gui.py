#!/usr/bin/env python3
"""
TODO add description
"""

import csv
import os

import pyperclip
import PySimpleGUI as psg

import bom
import common
import inventory
import partsearcher
import popups


_event_registry = []
_current_tab = 'Inventory'


class RegistryEvent:
    def __init__(self, event_id, func, matcher=None, pass_event=False):
        self.event_id = event_id
        self.func = func
        self.matcher = matcher
        self.pass_event = pass_event
        _event_registry.append(self)

    def __eq__(self, __value: object) -> bool:
        return self.matcher(self.event_id, __value) if self.matcher else self.event_id == __value


class SectionTable:
    def __init__(self, headings, key, name):
        self.key = key
        self.name = name
        self._cell_copy_str = f'Copy Selected {name} Cell'
        self._row_copy_str = f'Copy Selected {name} Row as CSV'
        self.table = psg.Table(
            headings=headings,
            values=[],
            col_widths=[len(item) for item in headings],
            auto_size_columns=False,
            key=key,
            hide_vertical_scroll=False,
            vertical_scroll_only=False,
            right_click_menu=['', [self._cell_copy_str, self._row_copy_str]],
            enable_click_events=True
        )
        self.row = 0
        self.col = 0
        self._bound = False

    def _click_matcher(self, event, other):
        # Exclude the position, just match the click event
        return hasattr(event, '__iter__') and (other[:2] == event)
    
    def _get_inner(self, lst, idx1, idx2, default=None):
        if hasattr(lst, '__iter__') and len(lst) >= (idx1 + 1):
            inner_lst = lst[idx1]
            if hasattr(inner_lst, '__iter__') and len(inner_lst) >= (idx2 + 1):
                return inner_lst[idx2]
        return default
    
    def _update_pos(self, event):
        if hasattr(event, '__iter__') and len(event) >= 3:
            r = self._get_inner(event, 2, 0)
            c = self._get_inner(event, 2, 1)
            if isinstance(r, int) and isinstance(c, int) and r >= 0 and c >= 0:
                self.row, self.col = event[2]

    def _row_copy_action(self):
        row = self.get_selected_row(fmt=False)
        if not row:
            return
        elif hasattr(row, '__iter__'):
            # Convert all cells to str; some elements are int
            row = [str(r) for r in row]
            pyperclip.copy(','.join(row))
        elif any([isinstance(row, t) for t in (str, int, float, bool)]):
            # pyperclip can by default only copy str, int, float, and bool
            # A list is expected, so this is primarily for futureproofing
            pyperclip.copy(row)

    def bind_click_events(self):
        if self._bound:
            return
        #TODO add ctrl-c copying of selected cell
        # Format for a click event is: (key, '+CLICKED+', (row, col))
        RegistryEvent((f'{self.key}', '+CLICKED+'), self._update_pos, self._click_matcher, pass_event=True)
        RegistryEvent(self._cell_copy_str, lambda: pyperclip.copy(self.get_selected_cell_value()))
        RegistryEvent(self._row_copy_str, self._row_copy_action)
        self._bound = True

    def get_selected_row(self, fmt=True):
        if len(self.SelectedRows) == 0:
            return None
        else:
            sel_table_row = self.Values[self.SelectedRows[0]]
            return {k: sel_table_row[i] for i, k in enumerate(self.ColumnHeadings)} if fmt else sel_table_row
        
    def get_selected_cell_value(self):
        return self.Values[self.row][self.col]
        
    def update_values(self, values):
        self.table.update(values=values)
    
    def clear_values(self):
        self.update_values([])

    @property
    def Values(self):
        return self.table.Values
    
    @property
    def ColumnHeadings(self):
        return self.table.ColumnHeadings
    
    @property
    def SelectedRows(self):
        return self.table.SelectedRows
    
    @property
    def Widget(self):
        return self.table.Widget


def _register_all_events():
    RegistryEvent('-BOM-OPEN-', lambda: bom.open_(values, rbom_table, pbom_subtables))
    RegistryEvent('-SELECT-SEARCH-QUERY-', lambda: search_query_input.update(disabled=False))
    RegistryEvent('-SELECT-SEARCH-PART-', lambda: search_query_input.update(disabled=True, value=''))
    RegistryEvent('-SEARCH-EXEC-', lambda: searcher.execute(values['-SEARCH-SRC-'], values['-SEARCH-QUERY-']))
    RegistryEvent('-PBOM-TAB-SWITCH-', _set_current_tab)
    RegistryEvent('-ASSOC-ITEM-PART-', _assoc_item_part)
    RegistryEvent('-RM-ITEM-PART-', _rm_item_part)

    RegistryEvent('Instructions', lambda: popups.info(popups.instructions_msg))
    RegistryEvent('Required BOM Fields', lambda: popups.info(bom.bom_fields_msg))
    RegistryEvent('About aggropart', lambda: popups.info(popups.about_msg))
    RegistryEvent('Export Current PBOM', lambda: _export_pbom(_current_tab))
    RegistryEvent('-EXPORT-C-PBOM-', lambda: _export_pbom(_current_tab))
    RegistryEvent('Export All PBOMs', _export_all_pboms)
    RegistryEvent('-EXPORT-A-PBOM-', _export_all_pboms)
    RegistryEvent('Clear Inventory Cache', inventory.clear_caches)
    RegistryEvent('Clear All Tables', _clear_tables)

    RegistryEvent('-INV-UPDATE-BEGIN-', lambda: search_updating_text.update(visible=True))
    RegistryEvent('-INV-UPDATE-END-', lambda: search_updating_text.update(visible=False))
    RegistryEvent('-INV-UPDATE-QUEUED-', lambda: searcher.update_gui_queued())


def _bind_table_clicks():
    rbom_table.bind_click_events()
    ssel_table.bind_click_events()
    for table in pbom_subtables.values():
        table.bind_click_events()


def _clear_tables():
    rbom_table.clear_values()
    ssel_table.clear_values()
    for table in pbom_subtables.values():
        table.clear_values()


def _export_pbom(src):
    table = pbom_subtables[src]
    with open(f'{bom.OUT_FOLDER}/{src.lower()}_bom_{bom.loaded_filename}.csv', 'w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(bom.altium_fields + [''] + table.ColumnHeadings)
        for part, item in zip(item_part_assoc_map[src], table.Values):
            writer.writerow(part + [''] + item)


def _export_all_pboms():
    for src in pbom_subtables.keys():
        _export_pbom(src)


def _assoc_item_part():
    #TODO check quantity requested by RBOM against SSEL
    rbom_row = rbom_table.get_selected_row(fmt=False)
    ssel_row = ssel_table.get_selected_row(fmt=False)
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
    rbom_table.update_values(new_rbom_values)

    new_pbom_values = pbom_table.Values
    new_pbom_values.append(ssel_row)
    pbom_table.update_values(new_pbom_values)

    item_part_assoc_map[searcher.last_src].append(rbom_row)


def _set_current_tab():
    global _current_tab
    _current_tab = values['-PBOM-TAB-SWITCH-']


def _rm_item_part():
    pbom_table = pbom_subtables[_current_tab]
    pbom_row = pbom_table.get_selected_row(fmt=False)
    if not pbom_row:
        popups.error('No Processed BOM row selected / row is invalid')
        return

    new_pbom_values = pbom_table.Values
    sel_idx = pbom_table.SelectedRows[0]
    new_pbom_values.pop(sel_idx)
    pbom_table.update_values(new_pbom_values)

    new_rbom_values = rbom_table.Values
    new_rbom_values.append(item_part_assoc_map[_current_tab][sel_idx])
    rbom_table.update_values(new_rbom_values)


def _make_table_tab(src):
    return psg.Tab(src, [[pbom_subtables[src].table]])


def _make_window():
    rbom_layout = [
        psg.Frame('Remaining BOM', [
            [psg.FileBrowse('Open BOM CSV', enable_events=True, key='-BOM-OPEN-')],
            [rbom_table.table]
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
                search_updating_text,
            ],
            [ssel_table.table]
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
    os.makedirs(bom.OUT_FOLDER, exist_ok=True)

    rbom_table = SectionTable(bom.altium_fields, '-RBOM-TABLE-', 'RBOM')
    ssel_table = SectionTable(bom.search_fields, '-SSEL-TABLE-', 'SSEL')
    pbom_subtables = {
        'Inventory': SectionTable(bom.inv_fields, '-INV-TABLE-', 'Inventory'),
        'Digikey': SectionTable(bom.dk_fields, '-DK-TABLE-', 'Digikey'),
        'Mouser': SectionTable(bom.mouser_fields, '-MOUSER-TABLE-', 'Mouser'),
        'JLCPCB': SectionTable(bom.jlc_fields, '-JLC-TABLE-', 'JLCPCB')
    }
    item_part_assoc_map = {k: [] for k in pbom_subtables.keys()}

    search_query_input = psg.Input(s=15, tooltip='Query', key='-SEARCH-QUERY-',
                                   disabled=True, disabled_readonly_background_color='#9c9c9c')
    search_updating_text = psg.Text('UPDATING', visible=False)

    window = _make_window()
    _pack_frame('-RBOM-FRAME-')
    _pack_frame('-SSEL-FRAME-')
    _pack_frame('-PBOM-FRAME-')

    searcher = partsearcher.PartSearcher(window, rbom_table, ssel_table)

    _register_all_events()
    _bind_table_clicks()

    while True:
        event, values = window.read()
        if event != '__TIMEOUT__':
            print(event, values)
        if event == psg.WIN_CLOSED or event == 'Exit':
            break

        for r_event in _event_registry:
            if r_event == event:
                if r_event.pass_event:
                    r_event.func(event)
                else:
                    r_event.func()
                break
