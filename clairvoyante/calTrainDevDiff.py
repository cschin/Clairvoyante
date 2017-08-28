import sys
import os
import argparse
import param
import pickle
import numpy as np
from threading import Thread

def Run(args):
    # create a Clairvoyante
    if args.v1 == True:
        import utils_v1 as utils
        if args.slim == True:
            import clairvoyante_v1_slim as cv
        else:
            import clairvoyante_v1 as cv
    elif args.v2 == True:
        import utils_v2 as utils
        if args.slim == True:
            import clairvoyante_v2_slim as cv
        else:
            import clairvoyante_v2 as cv
    elif args.v3 == True:
        import utils_v2 as utils # v3 network is using v2 utils
        if args.slim == True:
            import clairvoyante_v3_slim as cv
        else:
            import clairvoyante_v3 as cv
    utils.SetupEnv()
    m = cv.Clairvoyante()
    m.init()

    CalcAll(args, m, utils)

def CalcAll(args, m, utils):
    if args.bin_fn != None:
        with open(args.bin_fn, "rb") as fh:
            total = pickle.load(fh)
            XArrayCompressed = pickle.load(fh)
            YArrayCompressed = pickle.load(fh)
            posArrayCompressed = pickle.load(fh)
    else:
        total, XArrayCompressed, YArrayCompressed, posArrayCompressed = \
        utils.GetTrainingArray(args.tensor_fn,
                               args.var_fn,
                               args.bed_fn)

    predictBatchSize = param.predictBatchSize
    trainingTotal = int(total*param.trainingDatasetPercentage)
    validationStart = trainingTotal + 1
    numValItems = total - validationStart

    for n in args.chkpnt_fn:
        m.restoreParameters(os.path.abspath(n))
        datasetPtr = 0
        trainingLost = 0
        validationLost = 0
        i = 1
        XBatch, XNum, XEndFlag = utils.DecompressArray(XArrayCompressed, datasetPtr, predictBatchSize, total)
        YBatch, YNum, YEndFlag = utils.DecompressArray(YArrayCompressed, datasetPtr, predictBatchSize, total)
        datasetPtr += XNum
        while True:
            threadPool = []
            threadPool.append(Thread(target=m.getLossNoRT, args=(XBatch, YBatch, )))
            for t in threadPool: t.start()
            predictBatchSize = param.predictBatchSize
            if datasetPtr < validationStart and (validationStart - datasetPtr) < predictBatchSize:
                predictBatchSize = validationStart - datasetPtr
            elif datasetPtr >= validationStart and (datasetPtr % predictBatchSize) != 0:
                predictBatchSize = predictBatchSize - (datasetPtr % predictBatchSize)
            #print >> sys.stderr, "%d\t%d\t%d\t%d" % (datasetPtr, predictBatchSize, validationStart, total)
            XBatch2, XNum2, XEndFlag2 = utils.DecompressArray(XArrayCompressed, datasetPtr, predictBatchSize, total)
            YBatch2, YNum2, YEndFlag2 = utils.DecompressArray(YArrayCompressed, datasetPtr, predictBatchSize, total)
            if XNum != YNum or XEndFlag != YEndFlag:
                sys.exit("Inconsistency between decompressed arrays: %d/%d" % (XNum, YNum))
            for t in threadPool: t.join()
            XBatch = XBatch2; YBatch = YBatch2
            if datasetPtr >= validationStart: validationLost += m.getLossLossRTVal
            else: trainingLost += m.getLossLossRTVal
            if XEndFlag2!= 0:
                m.getLossNoRT( XBatch, YBatch )
                if datasetPtr >= validationStart: validationLost += m.getLossLossRTVal
                else: trainingLost += m.getLossLossRTVal
                print >> sys.stderr, "%s\t%.10f\t%.10f" % (n, trainingLost/trainingTotal, validationLost/numValItems)
                break;
            i += 1
            datasetPtr += XNum2


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
            description="Calculate the loss different between training dataset and validation dataset" )

    parser.add_argument('--bin_fn', type=str, default = None,
            help="Binary tensor input generated by tensor2Bin.py, tensor_fn, var_fn and bed_fn will be ignored")

    parser.add_argument('--tensor_fn', type=str, default = None,
            help="Tensor input")

    parser.add_argument('--var_fn', type=str, default = None,
            help="Truth variants list input")

    parser.add_argument('--bed_fn', type=str, default = None,
            help="High confident genome regions input in the BED format")

    parser.add_argument('--chkpnt_fn', nargs='+', type=str, default = None,
            help="Input a list of checkpoint for calculation")

    parser.add_argument('--v3', type=bool, default = True,
            help="Use Clairvoyante version 3")

    parser.add_argument('--v2', type=bool, default = False,
            help="Use Clairvoyante version 2")

    parser.add_argument('--v1', type=bool, default = False,
            help="Use Clairvoyante version 1")

    parser.add_argument('--slim', type=bool, default = False,
            help="Train using the slim version of Clairvoyante, optional")

    args = parser.parse_args()

    if len(sys.argv[1:]) == 0:
        parser.print_help()
        sys.exit(1)

    Run(args)

