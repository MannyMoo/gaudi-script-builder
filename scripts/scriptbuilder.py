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
    argparser.add_argument('--strippingList', default = '')
    argparser.add_argument('--aliases', default = '{}')
    argparser.add_argument('--labXAliases', action = 'store_true', default = False)
    argparser.add_argument('--substitutions', default = '{}')
    argparser.add_argument('--optssuffix', default = 'settings')
    argparser.add_argument('--extraopts', default = '')
    argparser.add_argument('--extraoptsfile', default = '')
    argparser.add_argument('--useTrackScaleState', default = 'True')
    argparser.add_argument('--datatype', default = None)
    argparser.add_argument('--diracversion', default = None)
    argparser.add_argument('--force', action = 'store_true', default = False)
    args = argparser.parse_args()

    opts = DaVinciScript(args.outputfile, args.version, args.linename, args.datafile,
                         L0List = args.L0List.split(), 
                         HLT1List = args.HLT1List.split(),
                         HLT2List = args.HLT2List.split(), 
                         strippingList = args.strippingList.split(),
                         aliases = eval(args.aliases),
                         labXAliases = args.labXAliases,
                         substitutions = eval(args.substitutions),
                         optssuffix = args.optssuffix, 
                         extraopts = args.extraopts,
                         extraoptsfile = args.extraoptsfile,
                         useTrackScaleState = eval(args.useTrackScaleState),
                         datatype = args.datatype,
                         diracversion = args.diracversion,
                         force = args.force)
    fname = opts.write()
    print 'Created', fname
    return fname

if __name__ == '__main__' :
    main()
