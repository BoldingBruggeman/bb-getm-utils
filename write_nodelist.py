import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('nodes')
args = parser.parse_args()

match = re.match(r'(.*)\[(.*)\](.*)', args.nodes)
if match is not None:
    # Hostnames in PBS/SLURM notation, e.g., node[01-06]
    nodes = []
    left, middle, right = match.groups()
    for item in middle.split(','):
        if '-' in item:
            start, stop = item.split('-')
            for i in range(int(start), int(stop)+1):
                nodes.append('%s%s%s' % (left, str(i).zfill(len(start)), right))
        else:
            nodes.append('%s%s%s' % (left, item, right))
else:
    # Comma-separated hostnames
    nodes = args.nodes.split(',')

for node in nodes:
    print node