#!/usr/bin/env python3
"""
TODO add description
"""

import argparse
import csv
import sys


def main(args):
    pass


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    # input Altium BOM
    #validates all rows have Mouser, Digikey, JLC part numbers (or warn to ignore)
    # Do inventory search (Notion) to see which parts are already available (& remove)
    #  if None or multiple, ask user which is correct
    #  if no box, warn & provide link for user - option for manual override
    #  Subtract quantities from inventory if needed (& arg is passed)
    # If assembly flag passed, (and API key provided)
    #  search JLC and subtract all that are present
    #  if a part is OOS, ask for alt part num or to buy externally
    #  warn for extended parts (?)
    #  tally part cost, parts to order from JLC
    # For all remaining parts,
    #  provide digikey and mouser part costs (for diff groupings)
    #  user selects each src & qty (unless part only exists on one)
    #  create importable BOM for Mouser and Digikey separately at end



if __name__ == "__main__":
    args = _parse_args()
    sys.exit(main(args))
