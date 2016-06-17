#!/bin/env python
'''Get data files from bookkeeping. Has to be run with Ganga.'''

from GaudiScriptBuilder.GangaUtils import BKDataGetter
from argparse import ArgumentParser

def main() :
    argparser = ArgumentParser()
    argparser.add_argument('--paths')
    argparser.add_argument('--destDir', default = '.')

    args = argparser.parse_args()

    if ',' in args.paths :
        paths = eval(args.paths)
    else :
        paths = (args.paths,)
    
    for bkpath in paths :
        try :
            bkpath, fname = bkpath
            getter = BKDataGetter(bkpath)
        except :
            getter = BKDataGetter(bkpath)
            fname = getter.get_file_name()
        datafile = getter.save_data_file(destDir = args.destDir, fname = fname)
        print bkpath, ':', datafile

if __name__ == '__main__' :
    main()
