#!/bin/env python

from GaudiScriptBuilder.EnvUtils import get_lhcb_env
from argparse import ArgumentParser

def main() :
    argparser = ArgumentParser()
    argparser.add_argument('-f', '--datafile')
    argparser.add_argument('--explicittags', action = 'store_true', default = False)
    argparser.add_argument('--optssuffix', default = 'settings')
    argparser.add_argument('--datatype', default = None)
    argparser.add_argument('--diracversion', default = None)
    argparser.add_argument('--noforce', action = 'store_true', default = False)
    args = argparser.parse_args()

    dvenv = get_lhcb_env('DaVinci')
    cmd = '''from GaudiScriptBuilder.AppConfig import get_data_opts
get_data_opts(datafile = {0!r}, explicitTags = {1!r}, suffix = {2!r}, datatype = {3!r}, diracversion = {4!r}, force = {5!r})
'''.format(args.datafile, args.explicittags, args.optssuffix, args.datatype, args.diracversion, (not args.noforce))
    retval = dvenv.eval_python(cmd)
    if retval['exitcode'] != 0 :
        print 'cmd:'
        print cmd
        print 'stdout:'
        print retval['stdout']
        print 'stderr:'
        print retval['stderr']

if __name__ == '__main__' :
    main()
