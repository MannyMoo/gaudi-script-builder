#!/bin/env python

from argparse import ArgumentParser
import subprocess

def main() :
    from GaudiScriptBuilder.AppConfig import DaVinciScript

    argparser = ArgumentParser()
    argparser.add_argument('--datafile')
    argparser.add_argument('--linename')
    argparser.add_argument('--version')
    argparser.add_argument('--outputfile')
    argparser.add_argument('--L0List', default = '')
    argparser.add_argument('--HLT1List', default = '')
    argparser.add_argument('--HLT2List', default = '')
    args = argparser.parse_args()

    opts = DaVinciScript(args.outputfile, args.version, args.linename, args.datafile,
                         L0List = args.L0List.split(), HLT1List = args.HLT1List.split(),
                         HLT2List = args.HLT2List.split())
    fname = opts.write()
    print 'Created', fname
    return fname

if __name__ == '__main__' :
    main()
