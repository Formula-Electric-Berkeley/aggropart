import ingress
import csv
import common

common.init_env()

class Args:
    def __init__(self):
        self.ingress_type = 'part'
        self.distributor = 'digikey'
        self.box = None
        self.quantity = None
        self.part = None
        self.passive = True
        self.refresh = False

args = Args()

with open('xs0006.csv', 'r') as f:
    reader = csv.reader(f)
    for line in reader:
        box, quantity, part = line
        args.box = box
        args.quantity = int(quantity)
        args.part = part
        ingress.main(args)
