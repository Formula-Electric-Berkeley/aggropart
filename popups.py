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
    psg.PopupNoButtons(msg, title='aggropart')


def error(err):
    psg.Popup(err)
