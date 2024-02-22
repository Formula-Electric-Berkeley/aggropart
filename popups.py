import logging

import PySimpleGUI as psg

import common

instructions_msg = f"""
For instructions on how to use this program, see the
README.md file included with this repository.

It can also be viewed on the web at 
https://github.com/Formula-Electric-Berkeley/aggropart/blob/master/README.md
"""

# The GUI font is not monospaced
about_msg = f"""
                           aggropart
  A utility program to automate the selection of 
             parts from an Altium BOM file.

             Copyright (c) 2023 boomaa23
                 aggropart.aptapus.net
github.com/Formula-Electric-Berkeley/aggropart
                 github.com/boomaa23
                 
                       Version {common.VERSION}
"""


def info(msg):
    logging.info(msg)
    psg.PopupNoButtons(msg, title='aggropart-info')


def error(err):
    logging.error(err)
    psg.Popup(err, title='aggropart-error')


def confirm(msg):
    layout = [[
        psg.Text(msg), 
        psg.Button(button_text='Yes', key='-YES-'),
        psg.Button(button_text='No', key='-NO-')
    ]]
    
    window = psg.Window('aggropart-confirm', layout, modal=True, grab_anywhere=True, finalize=True)
    window['-YES-'].bind('<Return>', 'ENTER-')

    while True:
        event, _ = window.read()
        if event == psg.WIN_CLOSED or event == 'Exit' or event == '-CANCEL-':
            window.close()
            return False
        elif event == '-YES-' or event == '-YES-ENTER-':
            window.close()
            return True
        elif event == '-NO-':
            window.close()
            return False


def input_(msg, tooltip=None, default=None, validator=(lambda v: True)):
    layout = [[
        psg.Text(msg), 
        psg.Input(s=15, tooltip=(msg if tooltip is None else tooltip), default_text=default, key='-IPT-'),
        psg.Button(button_text='OK', key='-OK-'),
        psg.Button(button_text='Cancel', key='-CANCEL-')
    ]]
    
    window = psg.Window('aggropart-input', layout, modal=True, grab_anywhere=True, finalize=True)
    window['-IPT-'].bind('<Return>', 'ENTER-')

    while True:
        event, values = window.read()
        if event == psg.WIN_CLOSED or event == 'Exit' or event == '-CANCEL-':
            window.close()
            return False
        if event == '-OK-' or event == '-IPT-ENTER-':
            if validator(values['-IPT-']):
                window.close()
                return values['-IPT-']
            

def validate_int(v):
    try:
        _ = int(v)
        return True
    except:
        error('Value entered was not an integer')
