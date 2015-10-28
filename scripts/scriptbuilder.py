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
    
    args = argparser.parse_args()

    opts = DaVinciScript(args.outputfile, args.version, args.linename, args.datafile)
    fname = opts.write()
    print 'Created', fname
    return fname

if __name__ == '__main__' :
    main()
