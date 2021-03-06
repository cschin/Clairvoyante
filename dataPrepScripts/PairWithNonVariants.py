import os
home_dir = os.path.expanduser('~')
import sys
sys.path.append(home_dir+'/miniconda2/lib/python2.7/site-packages')
import intervaltree
import argparse
import logging
import random
import subprocess
import shlex

logging.basicConfig(format='%(message)s', level=logging.INFO)


def Run(args):
    Pair(args)


def bufcount(filename):
    f = subprocess.Popen(shlex.split("gzip -fdc %s" % (filename) ), stdout=subprocess.PIPE, bufsize=8388608)
    lines = 0
    buf_size = 1024 * 1024
    read_f = f.stdout.read

    buf = read_f(buf_size)
    while buf:
        lines += buf.count('\n')
        buf = read_f(buf_size)
    f.stdout.close()
    f.wait()

    return lines


def Pair(args):
    tree = {}
    if args.bed_fn != None:
        logging.info("Loading BED file ...")
        f = subprocess.Popen(shlex.split("gzip -fdc %s" % (args.bed_fn) ), stdout=subprocess.PIPE, bufsize=8388608)
        for row in f.stdout:
            row = row.strip().split()
            name = row[0]
            if name not in tree:
                tree[name] = intervaltree.IntervalTree()
            begin = int(row[1])
            end = int(row[2])
            tree[name].addi(begin, end)
        f.stdout.close()
        f.wait()

    logging.info("Counting the number of Truth Variants in %s ..." % args.tensor_var_fn)
    v = 0
    d = {}
    f = subprocess.Popen(shlex.split("gzip -fdc %s" % (args.tensor_var_fn) ), stdout=subprocess.PIPE, bufsize=8388608)
    for row in f.stdout:
        row = row.strip().split()
        ctgName = row[0]
        pos = int(row[1])
        key = "-".join([ctgName, str(pos)])
        v += 1
        d[key] = 1
    f.stdout.close()
    f.wait()

    logging.info("%d Truth Variants" % v)
    t = v * args.amp
    logging.info("%d non-variants to be picked" % t)

    logging.info("Counting the number of usable non-variants in %s ..." % args.tensor_can_fn)
    c = 0
    f = subprocess.Popen(shlex.split("gzip -fdc %s" % (args.tensor_can_fn) ), stdout=subprocess.PIPE, bufsize=8388608)
    for row in f.stdout:
        row = row.strip().split()
        ctgName = row[0]
        pos = int(row[1])
        if args.bed_fn != None:
            if ctgName not in tree:
                continue
            if len(tree[ctgName].search(pos)) == 0:
                continue
        key = "-".join([ctgName, str(pos)])
        if key in d:
            continue
        c += 1
    f.stdout.close()
    f.wait()
    logging.info("%d usable non-variant" % c)

    r = float(t) / c
    r = r if r <= 1 else 1
    logging.info("%.2f of all non-variants are selected" % r)


    o1 = 0
    o2 = 0
    output_fpo = open(args.output_fn, "wb")
    output_fh = subprocess.Popen(shlex.split("gzip -c"), stdin=subprocess.PIPE, stdout=output_fpo, stderr=sys.stderr, bufsize=8388608)
    f = subprocess.Popen(shlex.split("gzip -fdc %s" % (args.tensor_var_fn) ), stdout=subprocess.PIPE, bufsize=8388608)
    for row in f.stdout:
        row = row.strip()
        output_fh.stdin.write(row)
        output_fh.stdin.write("\n")
        o1 += 1
    f.stdout.close()
    f.wait()
    f = subprocess.Popen(shlex.split("gzip -fdc %s" % (args.tensor_can_fn) ), stdout=subprocess.PIPE, bufsize=8388608)
    for row in f.stdout:
        rawRow = row.strip()
        row = rawRow.split()
        ctgName = row[0]
        pos = int(row[1])
        if args.bed_fn != None:
            if ctgName not in tree:
                continue
            if len(tree[ctgName].search(pos)) == 0:
                continue
        key = "-".join([ctgName, str(pos)])
        if key in d:
            continue
        if random.random() < r:
            output_fh.stdin.write(rawRow)
            output_fh.stdin.write("\n")
            o2 += 1
    f.stdout.close()
    f.wait()
    output_fh.stdin.close()
    output_fh.wait()
    output_fpo.close()
    logging.info("%.2f/%.2f Truth Variants/Non-variants outputed" % (o1, o2))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
            description="Predict and compare using Clairvoyante" )

    parser.add_argument('--tensor_can_fn', type=str, default = None,
            help="Candidiate variant tensors input")

    parser.add_argument('--tensor_var_fn', type=str, default = None,
            help="Candidiate variant tensors input")

    parser.add_argument('--bed_fn', type=str, default = None,
            help="High confident genome regions input in the BED format")

    parser.add_argument('--output_fn', type=str, default = None,
            help="Tensors output file name")

    parser.add_argument('--amp', type=float, default = 2,
        help="Pick ((# of the Truth Variants)*amp) non-variants to pair with the Truth Variants, default: 2")

    args = parser.parse_args()

    if len(sys.argv[1:]) == 0:
        parser.print_help()
        sys.exit(1)

    Run(args)

