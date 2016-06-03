
import os, sys

if not os.environ.has_key('GANGASYSROOT') :
    raise EnvironmentError('''Environment variable GANGASYSROOT is undefined! Can\'t import Ganga GPI!
Do 

SetupProject Ganga

and try again.''')

sys.path.insert(0, os.path.normpath('{gangaSys}{sep}..{sep}install{sep}ganga{sep}python'\
                                        .format(gangaSys=os.environ['GANGASYSROOT'], sep = os.sep)))

from Ganga.GPI import BKQuery, LocalFile, export

def get_bk_path(bkpath) :
    '''Remove the sim+std:/ or evt+std:/ prefix from a bookkeeping path, if it's there. 
    If it's evt+std, convert it to sim+std format as required by BKQuery.'''
    if ':/' in bkpath :
        itype = bkpath.find(':/')
        pathType = bkpath[:itype]
        bkpath = bkpath[itype+2:]
        if 'evt+std' == pathType :
            splitPath = bkpath.split('/')
            evtType = splitPath.pop(3)
            splitPath.insert(len(splitPath)-1, evtType)
            bkpath = '/'.join(splitPath)
    return bkpath

class BKDataGetter(object) :
    __slots__ = ('bkpath', 'dqflag')

    def __init__(self, bkpath, dqflag = 'OK') :
        self.bkpath = get_bk_path(bkpath)
        self.dqflag = dqflag

    def get_file_name(self) :
        '''Convert a bookkeeping path to a .py file name.'''
        return self.bkpath[1:].replace('/', '_').replace(' ', '_') + '.py'

    def get_data_set(self) :
        data = BKQuery(type = 'Path', path = self.bkpath, dqflag = self.dqflag).getDataset()
        if not data :
            print 'Failed to retrieve data using path', self.bkpath
            return None
        return data

    def save_data_file(self, destDir = '.', fname = None, savecatalog = True,
                       saveganga = True) :
        data = self.get_data_set()
        if not data :
            return None
        if not fname :
            fname = os.path.join(destDir, self.get_file_name())
        else :
            fname = os.path.join(destDir, fname)

        if not '$' in fname :
            fname = os.path.abspath(fname)
            expandedfname = fname
        else :
            expandedfname = os.path.abspath(os.path.expandvars(fname))

        if savecatalog :
            catalogname = fname + '.xml'
            expandedcatalogname = expandedfname + '.xml'
            with open(expandedcatalogname, 'w') as f :
                f.write(data.getCatalog())
            data.XMLCatalogueSlice = LocalFile(namePattern = catalogname)
        if saveganga :
            export(data, expandedfname + '.ganga')

        with open(expandedfname, 'w') as f :
            f.write(data.optionsString())
            if savecatalog :
                f.write('\nfrom Gaudi.Configuration import FileCatalog\nFileCatalog().Catalogs += [{0!r}]\n'.format('xmlcatalog_file:' + catalogname))
        return fname
