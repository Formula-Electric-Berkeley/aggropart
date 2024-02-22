#!/usr/bin/env python3
"""
TODO add description
"""

import csv
import logging
import os
import pickle as pkl
import webbrowser

import pyperclip
import PySimpleGUI as psg

import audit
import bom
import common
import inventory
import partsearcher
import popups


_event_registry = []
_current_tab = 'Inventory'
#TODO add PEP8 linter to this project (+checkstyle)
#TODO move non-gui util files into util directory (difficult bc dependencies)
#TODO add autosave
#TODO make the search less bad (or perhaps the "part" option can have a selectable field)
#TODO add right click copy to top menu (difficult bc of use of optional_key to remove table names from right click menu)
#TODO have pbom show qty has, qty will use (i.e. separate)
#TODO only make item assoc-able if there is enough in SSEL
#TODO add an "ignore" SSEL category
#TODO make an "aggregate" mode for multiple BOMs (def behavior is to clear all)
#TODO option to change from DEBUG to INFO output mode (default to INFO perhaps)


class AutosaveObject:
    def __init__(self, obj_name):
        self.filepath = f'cache/autosave_{obj_name}.pkl'

    def update(self, values):
        with open(self.filepath, 'wb') as f:
            f.write(pkl.dumps(values))
            f.flush()


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
        self._cell_copy_str = f'Copy Selected Cell::{name}'
        self._row_copy_str = f'Copy Selected Row as CSV::{name}'
        self._ctrlc_event_id = f'-{self.name}-CTRLC-'
        self.table = psg.Table(
            headings=headings,
            values=[],
            col_widths=[len(item) for item in headings],
            auto_size_columns=False,
            key=key,
            hide_vertical_scroll=False,
            vertical_scroll_only=False,
            right_click_menu=['', [self._cell_copy_str, self._row_copy_str]],
            enable_click_events=True,
            right_click_selects=True
        )
        self.column_headings = headings
        self.row = -1
        self.col = -1
        self._bound = False
        self.autosave = AutosaveObject(self.name)

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
                window.bind('<Control-C>', self._ctrlc_event_id)
                window.bind('<Control-c>', self._ctrlc_event_id)
                self._trigger_hyperlink()

    def _trigger_hyperlink(self):
        cell_value = self.get_selected_cell_value()
        if type(cell_value) == str and cell_value.startswith('https://'):
            if popups.confirm(f'Do you want to proceed to {cell_value}?'):
                webbrowser.open_new_tab(cell_value)

    def _row_copy_action(self):
        row = self.get_selected_row(fmt=False)
        if row is None:
            popups.error('No row selected to copy')
            return
        elif hasattr(row, '__iter__'):
            # Convert all cells to str; some elements are int
            row = [str(r) for r in row]
            pyperclip.copy(','.join(row))
        elif any([isinstance(row, t) for t in (str, int, float, bool)]):
            # pyperclip can by default only copy str, int, float, and bool
            # A list is expected, so this is primarily for futureproofing
            pyperclip.copy(row)

    def _cell_copy_action(self):
        cell_value = self.get_selected_cell_value()
        if cell_value is not None:
            pyperclip.copy(cell_value)
        else:
            popups.error('No cell selected to copy')
            return

    def bind_click_events(self):
        if self._bound:
            return
        # Format for a click event is: (key, '+CLICKED+', (row, col))
        RegistryEvent((f'{self.key}', '+CLICKED+'), self._update_pos, self._click_matcher, pass_event=True)
        RegistryEvent(self._cell_copy_str, self._cell_copy_action)
        RegistryEvent(self._row_copy_str, self._row_copy_action)
        RegistryEvent(self._ctrlc_event_id, self._cell_copy_action)
        self._bound = True

    def get_selected_row(self, fmt=True):
        if len(self.SelectedRows) == 0:
            return None
        else:
            sel_table_row = self.Values[self.SelectedRows[0]]
            return {k: sel_table_row[i] for i, k in enumerate(self.ColumnHeadings)} if fmt else sel_table_row
        
    def get_selected_cell_value(self):
        if self.row >= 0 and self.col >= 0 and \
                len(self.Values) > self.row and \
                len(self.Values[self.row]) > self.col:
            return self.Values[self.row][self.col]
        
    def update_values(self, values):
        self.autosave.update(values)
        self.table.update(values=values)
    
    def clear_values(self):
        self.update_values([])

    def remove_row(self, row):
        self.table.Values.remove(row)

    def update_headings(self, headings):
        # ColumnHeadings property is final
        padded_headings = headings + [''] * (len(self.ColumnHeadings) - len(headings))
        for cid, text in zip(self.ColumnHeadings, padded_headings):
            self.table.Widget.heading(cid, text=text)
        self.column_headings = padded_headings

    @property
    def Values(self):
        return self.table.Values
    
    @property
    def ColumnHeadings(self):
        # ColumnHeadings property is final; this accounts for updates
        return self.column_headings
    
    @property
    def SelectedRows(self):
        return self.table.SelectedRows


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
    RegistryEvent('Clear All Tables', _clear_tables)

    RegistryEvent('Clear Cache::Inventory', inventory.clear_caches)
    RegistryEvent('Change Cache Timeout::Inventory', lambda: inventory.set_cache_timeout(popups.input_(
        msg='New cache timeout (in seconds): ', default=os.environ['CACHE_TIMEOUT_SEC'], validator=popups.validate_int)))
    RegistryEvent('Export to JSON::Inventory', lambda: False) #TODO
    RegistryEvent('Insert Item::Inventory', lambda: False) #TODO
    RegistryEvent('Count All Items', lambda: popups.info(audit.all_boxes(count=True)))
    RegistryEvent('Query All Value', lambda: popups.info(audit.all_boxes(count=False)) if
                  popups.confirm('This action consumes A LOT of Digikey API requests.'
                                 ' There is a daily limit of 1000. Are you sure you want to continue?') else None)
    RegistryEvent('Count Box Items', lambda: audit.selected_boxes_gui(count=True))
    RegistryEvent('Query Box Value', lambda: popups.info(audit.selected_boxes_gui(count=False)) if
                  popups.confirm('This action consumes a significant number of Digikey API requests.'
                                 ' There is a daily limit of 1000. Are you sure you want to continue?') else None)

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
    fn = f'{bom.OUT_FOLDER}/{src.lower()}_bom_{bom.loaded_filename}.csv'
    with open(fn, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(bom.altium_fields + [''] + table.ColumnHeadings)
        for part, item in zip(item_part_assoc_map[src], table.Values):
            writer.writerow(part + [''] + item)


def _export_all_pboms():
    for src in pbom_subtables.keys():
        _export_pbom(src)


def _find_row_qty(table, search_terms):
    row = table.get_selected_row(fmt=False)
    for s in search_terms:
        idx = table.ColumnHeadings.index(s)
        qty = row[idx] if s in table.ColumnHeadings else None
        if qty is not None:
            return int(qty), idx


def _assoc_item_part():
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
    
    rbom_qty, _ = _find_row_qty(rbom_table, ('Quantity',))
    ssel_qty, ssel_qty_idx = _find_row_qty(ssel_table, ('Quantity', 'Quantity Available', 'Stock'))

    if rbom_qty is not None and ssel_qty is not None and rbom_qty > ssel_qty:
        if not popups.confirm(f'Source quantity {ssel_qty} is less than BOM quantity {rbom_qty}. Proceed anyways?'):
            return

    pbom_table = pbom_subtables[searcher.last_src]
    new_rbom_values = rbom_table.Values
    new_rbom_values.pop(rbom_table.SelectedRows[0])
    rbom_table.update_values(new_rbom_values)

    new_pbom_values = pbom_table.Values
    new_pbom_values.append(ssel_row)
    pbom_table.update_values(new_pbom_values)

    item_part_assoc_map[searcher.last_src].append(rbom_row)
    item_part_assoc_map_autosave.update(item_part_assoc_map)

    #TODO remove used quantity from SSEL (needs to not be reflected on inventory cache 
    # but reflected on future reloads of inventory within the same session)

    # if ssel_qty <= rbom_qty:
    #     # Remove SSEL row if there are <= 0 remaining after RBOM
    #     ssel_table.remove_row(ssel_table.Values[ssel_table.row])
    # else:
    #     # Otherwise, subtract the RBOM quantity used from the SSEL quantity
    #     ssel_table.Values[ssel_table.row][ssel_qty_idx] -= rbom_qty
    # ssel_table.update_values(ssel_table.Values)


def _set_current_tab():
    global _current_tab
    _current_tab = values['-PBOM-TAB-SWITCH-']


def _rm_item_part():
    pbom_table = pbom_subtables[_current_tab]
    pbom_row = pbom_table.get_selected_row(fmt=False)
    if not pbom_row:
        popups.error('No Processed BOM row selected / row is invalid')
        return

    pbom_values = pbom_table.Values
    sel_idx = pbom_table.SelectedRows[0]
    pbom_values.pop(sel_idx)
    pbom_table.update_values(pbom_values)

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

    file_opts = ['Export Current PBOM', 'Export All PBOMs', 'Clear All Tables']
    advanced_inv_opts = ['Get Page by ID', 'Get Page Properties by ID', 'Get DB by ID']
    audit_opts = ['Count All Items', 'Count Box Items', 'Query Box Value', 'Query All Value']
    inventory_opts = ['Clear Cache::Inventory', 'Change Cache Timeout::Inventory', 
                      'Export to JSON::Inventory', 'Insert Item::Inventory', 
                      'Audit', audit_opts, 'Advanced', advanced_inv_opts]
    help_opts = ['Instructions', 'Required BOM Fields', 'About aggropart']
    menu = [psg.Menu([['File', file_opts], ['Inventory', inventory_opts], ['Help', help_opts]], key='-MENUBAR-', p=0)]

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
    common.init_env()
    os.makedirs(bom.OUT_FOLDER, exist_ok=True)

    rbom_table = SectionTable(bom.altium_fields, '-RBOM-TABLE-', 'RBOM')
    ssel_table = SectionTable(bom.search_fields, '-SSEL-TABLE-', 'SSEL')
    pbom_subtables = {
        'Inventory': SectionTable(bom.inv_fields, '-INV-TABLE-', 'Inventory'),
        'Digikey': SectionTable(bom.dk_fields, '-DK-TABLE-', 'Digikey'),
        'Mouser': SectionTable(bom.mouser_fields, '-MOUSER-TABLE-', 'Mouser'),
        'JLCPCB': SectionTable(bom.jlc_fields, '-JLC-TABLE-', 'JLCPCB')
    }
    #TODO make this autosave less bad
    item_part_assoc_map = {k: [] for k in pbom_subtables.keys()}
    item_part_assoc_map_autosave = AutosaveObject('item_part_assoc')
    item_part_assoc_map.update([]) # Clear autosave
    logging.info('All tables initialized')

    search_query_input = psg.Input(s=15, tooltip='Query', key='-SEARCH-QUERY-',
                                   disabled=True, disabled_readonly_background_color='#9c9c9c')
    search_updating_text = psg.Text('UPDATING', visible=False)

    window = _make_window()
    _pack_frame('-RBOM-FRAME-')
    _pack_frame('-SSEL-FRAME-')
    _pack_frame('-PBOM-FRAME-')
    logging.info('Main window created and frames packed')

    searcher = partsearcher.PartSearcher(window, rbom_table, ssel_table)
    logging.info('PartSearcher initialized')

    _register_all_events()
    _bind_table_clicks()
    logging.info('All events registered')

    while True:
        event, values = window.read()
        if event != '__TIMEOUT__':
            logging.info(f'Event triggered: {event}')
            logging.debug(values)
        if event == psg.WIN_CLOSED or event == 'Exit':
            break

        for r_event in _event_registry:
            if r_event == event:
                if r_event.pass_event:
                    r_event.func(event)
                    logging.info(f'Event finished: {event}')
                else:
                    r_event.func()
                    logging.info(f'Event finished: {event}')
                break
