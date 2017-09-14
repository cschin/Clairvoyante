import os
import sys
import argparse
import shlex
import subprocess
import signal

class InstancesClass(object):
    def __init__(self):
        self.EVCInstance = None
        self.CTInstance = None
        self.CVInstance = None

    def poll(self):
        self.EVCInstance.poll()
        self.CTInstance.poll()
        self.CVInstance.poll()

c = InstancesClass();


def CheckRtCode(signum, frame):
    c.poll()
    #print >> sys.stderr, c.EVCInstance.returncode, c.CTInstance.returncode, c.CVInstance.returncode
    if c.EVCInstance.returncode != None and c.EVCInstance.returncode != 0:
        c.CTInstance.kill(); c.CVInstance.kill()
        sys.exit("ExtractVariantCandidates.py exited with exceptions. Exiting...");

    if c.CTInstance.returncode != None and c.CTInstance.returncode != 0:
        c.EVCInstance.kill(); c.CVInstance.kill()
        sys.exit("CreateTensors.py exited with exceptions. Exiting...");

    if c.CVInstance.returncode != None and c.CVInstance.returncode != 0:
        c.EVCInstance.kill(); c.CTInstance.kill()
        sys.exit("callVar.py exited with exceptions. Exiting...");

    if c.EVCInstance.returncode == None or c.CTInstance.returncode == None or c.CVInstance.returncode == None:
        signal.alarm(5)


def CheckFileExist(fn, sfx=""):
    if not os.path.isfile(fn+sfx):
        sys.exit("Error: %s not found" % (fn+sfx))
    return os.path.abspath(fn)

def CheckCmdExist(fn):
    try:
        subprocess.check_output("which %s" % (fn), shell=True)
    except:
        sys.exit("Error: %s executable not found" % (fn))
    return fn

def Run(args):
    basedir = os.path.dirname(__file__)
    EVCBin = CheckFileExist(basedir + "/../dataPrepScripts/ExtractVariantCandidates.py")
    CTBin = CheckFileExist(basedir + "/../dataPrepScripts/CreateTensor.py")
    CVBin = CheckFileExist(basedir + "/callVar.py")
    pypyBin = CheckCmdExist(args.pypy)
    samtoolsBin = CheckCmdExist(args.samtools)
    chkpnt_fn = CheckFileExist(args.chkpnt_fn, sfx=".meta")
    bam_fn = CheckFileExist(args.bam_fn)
    ref_fn = CheckFileExist(args.ref_fn)
    call_fn = args.call_fn
    threshold = args.threshold
    minCoverage = args.minCoverage
    sampleName = args.sampleName
    if args.showRef == True:
        showRef = "True"
    else:
        showRef = "False"
    ctgName = args.ctgName
    if args.ctgStart and args.ctgEnd and int(args.ctgStart) <= int(args.ctgEnd):
        ctgRange = "--ctgStart %s --ctgEnd %s" % (args.ctgStart, args.ctgEnd)
    else:
        ctgRange = ""

    try:
        c.EVCInstance = subprocess.Popen(\
            shlex.split("%s %s --bam_fn %s --ref_fn %s --ctgName %s %s --threshold %s --minCoverage %s --samtools %s" %\
                        (pypyBin, EVCBin, bam_fn, ref_fn, ctgName, ctgRange, threshold, minCoverage, samtoolsBin) ),\
                        stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=8388608)
        c.CTInstance = subprocess.Popen(\
            shlex.split("%s %s --bam_fn %s --ref_fn %s --ctgName %s %s --samtools %s" %\
                        (pypyBin, CTBin, bam_fn, ref_fn, ctgName, ctgRange, samtoolsBin) ),\
                        stdin=c.EVCInstance.stdout, stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=8388608)
        c.CVInstance = subprocess.Popen(\
            shlex.split("python %s --chkpnt_fn %s --call_fn %s --sampleName %s --showRef %s" %\
                        (CVBin, chkpnt_fn, call_fn, sampleName, showRef) ),\
                        stdin=c.CTInstance.stdout, stdout=sys.stderr, stderr=sys.stderr, bufsize=8388608)
    except Exception as e:
        print e
        sys.exit("Failed to start required processes. Exiting...")

    signal.signal(signal.SIGALRM, CheckRtCode)
    signal.alarm(2)

    c.EVCInstance.stdout.close()
    c.EVCInstance.wait()
    c.CTInstance.stdout.close()
    c.CTInstance.wait()
    c.CTInstance.wait()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
            description="Call variants using a trained Clairvoyante model and a BAM file" )

    parser.add_argument('--chkpnt_fn', type=str, default = None,
            help="Input a checkpoint for testing or continue training")

    parser.add_argument('--ref_fn', type=str, default="ref.fa",
            help="Reference fasta file input, default: %(default)s")

    parser.add_argument('--bam_fn', type=str, default="bam.bam",
            help="BAM file input, default: %(default)s")

    parser.add_argument('--call_fn', type=str, default = None,
            help="Output variant predictions")

    parser.add_argument('--threshold', type=float, default=0.125,
            help="Minimum allele frequence of the 1st non-reference allele for a site to be considered as a condidate site, default: %(default)f")

    parser.add_argument('--minCoverage', type=float, default=4,
            help="Minimum coverage required to call a variant, default: %(default)d")

    parser.add_argument('--sampleName', type=str, default = "SAMPLE",
            help="Define the sample name to be shown in the VCF file")

    parser.add_argument('--ctgName', type=str, default="chr17",
            help="The name of sequence to be processed, default: %(default)s")

    parser.add_argument('--ctgStart', type=int, default=None,
            help="The 1-bsae starting position of the sequence to be processed")

    parser.add_argument('--ctgEnd', type=int, default=None,
            help="The inclusive ending position of the sequence to be processed")

    parser.add_argument('--samtools', type=str, default="samtools",
            help="Path to the 'samtools', default: %(default)s")

    parser.add_argument('--pypy', type=str, default="pypy",
            help="Path to the 'pypy', default: %(default)s")

    parser.add_argument('--showRef', type=bool, default = False,
            help="Show reference calls, optional")

    parser.add_argument('--v3', type=bool, default = True,
            help="Use Clairvoyante version 3")

    parser.add_argument('--v2', type=bool, default = False,
            help="Use Clairvoyante version 2")

    parser.add_argument('--slim', type=bool, default = False,
            help="Train using the slim version of Clairvoyante, optional")

    args = parser.parse_args()

    if len(sys.argv[1:]) == 0:
        parser.print_help()
        sys.exit(1)

    Run(args)