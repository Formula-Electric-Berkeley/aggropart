import PySimpleGUI as psg

import bom
import common


bom_fields_msg = f"""
The following BOM fields are required from Altium
{common.pfmt(bom.required_fields)}
The following BOM fields are optional from Altium
{common.pfmt(bom.optional_fields)}
"""

instructions_msg = f"""
For instructions on how to use this program, see the
README.md file included with this repository.

It can also be viewed on the web at 
https://github.com/Berkeley-Formula-Electric/aggropart/blob/master/README.md
"""

# The GUI font is not monospaced
about_msg = f"""
                           aggropart
  A utility program to automate the selection of 
             parts from an Altium BOM file.

             Copyright (c) 2023 boomaa23
                 aggropart.aptapus.net
github.com/Berkeley-Formula-Electric/aggropart
                 github.com/boomaa23
                 
                       Version {common.version}
"""


def info(msg):
    psg.PopupNoButtons(msg, title='aggropart')


def error(err):
    psg.Popup(err)
