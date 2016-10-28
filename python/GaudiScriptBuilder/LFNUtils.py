'''Tools for retrieving info on datafile LFNs. Requires LHCbDirac to be setup
and a valid grid proxy.'''

import glob, subprocess, os
def get_dirac_python_env() :
    cmd = '''
import os
env = {}
for var in 'PYTHONPATH', 'LD_LIBRARY_PATH' :
    env[var] = filter(lambda x : 'dirac' in x.lower(), os.environ[var].split(':'))
print repr(env)
'''
    proc = subprocess.Popen('lb-run LHCbDirac python -c'.split() + [cmd],
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    success = (proc.wait() == 0)
    stdout = proc.stdout.readlines()
    stderr = proc.stderr.readlines()
    proc.stdout.close()
    proc.stderr.close()
    if not success :
        return None
    try :
        pypath = eval(stdout[-1])
    except :
        return None
    return pypath

try :
    import DIRAC
except ImportError as ex :
    #raise ex
    # This doesn't currently work, possibly due to a python version mismatch
    # between the version used to call the script and that used to retrieve
    # the environment.
    diracpyenv = get_dirac_python_env()
    if not diracpyenv :
        raise ex
    import sys
    sys.path += diracpyenv['PYTHONPATH']
    for var, val in diracpyenv.iteritems() :
        os.environ[var] = ':'.join(val) + ':' + os.environ[var]
    import DIRAC

import  DIRAC.Core.Base.Script as Script
from LHCbDIRAC.DataManagementSystem.Client.DMScript import DMScript

'''Really not sure why this is necessary, but without it I get the message
"ERROR: Failed to get file metadata: Cannot get URL for Bookkeeping/BookkeepingManager in 
setup LHCb-Production: Option /DIRAC/Setups/LHCb-Production/Bookkeeping is not defined"
so it must do some setup as well.'''
Script.parseCommandLine(ignoreErrors = True)

from DIRAC.Core.DISET.RPCClient import RPCClient
from LHCbDIRAC.BookkeepingSystem.Client.BookkeepingClient import BookkeepingClient
from DIRAC.DataManagementSystem.Client.DataManager          import DataManager
from DIRAC.Resources.Catalog.FileCatalog                    import FileCatalog

from ROOT import TRandom3

class InitOnDemand(object) :
    def __init__(self, initialiser, *args, **kwargs) :
        self.initialiser = initialiser
        self.args = args
        self.kwargs = kwargs
        self.obj = None

    def _initobj(self) :
        self.obj = self.initialiser(*self.args, **self.kwargs)
        self.get = self._get
        return self.obj

    def _get(self) :
        return self.obj

    get = _initobj

    def __call__(self) :
        return self.get()

bk_manager = InitOnDemand(RPCClient, 'Bookkeeping/BookkeepingManager')
bk_client = InitOnDemand(BookkeepingClient)
file_catalog = InitOnDemand(FileCatalog)
data_manager = InitOnDemand(DataManager)

class LFNSet(object) :
    __slots__ = ('lfns', 'catalogName')

    def __init__(self, lfn1, *lfns) :
        self.lfns = {}
        self.catalogName = None
        self.add_lfns(lfn1, *lfns)

    def add_lfns(self, lfn1, *lfns) :
        for lfn in (lfn1,) + lfns :
            self.add_lfn(lfn)
    
    def add_lfn(self, lfn) :
        if isinstance(lfn, str) :
            if not self.has_lfn(lfn) :
                self.lfns[lfn] = {}
        elif isinstance(lfn, dict) :
            for iLFN, info in lfn.iteritems() :
                if not self.has_lfn(iLFN) :
                    self.lfns[iLFN] = dict(info)
                else :
                    self.lfns[iLFN].update(info)
        elif isinstance(lfn, LFNSet) :
            self.add_lfn(lfn.lfns)
    
    def has_lfn(self, lfn) :
        return self.lfns.has_key(lfn)

    def lfn_list(self) :
        return self.lfns.keys()

    def get_bk_metadata(self) :
        if not self.lfns :
            return True
        result = bk_manager().getFileMetadata(self.lfn_list())
        if not result['OK'] : 
            print 'ERROR: Failed to get file metadata: %s' % res['Message']
            return False
        lfnMetadata = result['Value'].get( 'Successful', result['Value'] )
        for lfn, info in lfnMetadata.iteritems() :
            self.lfns[lfn].update(info)
        return True

    def get_run_numbers(self) :
        if not self.lfns.values()[0].has_key('RunNumber') :
            self.get_bk_metadata()
        return set(info['RunNumber'] for info in self.lfns.values())

    def get_run_info(self, fields = None, statistics = None) :
        '''Default fields are: ['ConfigName', 'ConfigVersion', 'JobStart', 'JobEnd', 'TCK',
                               'FillNumber', 'ProcessingPass', 'ConditionDescription', 'CONDDB', 'DDDB']
        Default statistics are: ['NbOfFiles', 'EventStat', 'FileSize', 'FullStat',
                                'Luminosity', 'InstLumonosity', 'EventType']'''

        if not self.lfns :
            return True
            
        inDict = {}
        if fields :
            inDict['Fields'] = fields 
        if statistics :
            inDict['Statistics'] = statistics

        runs = self.get_run_numbers()
        runInfo = {}
        for runNo in runs :
            inDict['RunNumber'] = runNo
            runInfo.update(bk_client().getRunInformation(inDict)['Value'])

        for info in self.lfns.values() :
            info['RunInfo'] = runInfo[info['RunNumber']]
        return True

    def get_run_fields(self, field1, *fields) :
        return get_run_info(fields = [field1] + list(fields))

    def get_fill_number(self) :
        return self.get_run_fields('FillNumber')

    def get_iohelper_lines(self) :
        lines = '''
from Gaudi.Configuration import *
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles({0},
                            clear = True)
'''.format(repr(['LFN:' + lfn for lfn in self.lfns]).replace(',', ',\n'))
        if self.catalogName :
            lines += '''
from Gaudi.Configuration import FileCatalog
FileCatalog().Catalogs = ["xmlcatalog_file:{0}"]
'''.format(os.path.abspath(self.catalogName))
        return lines

    def make_datafile(self, fname) :
        if fname[-3:] != '.py' :
            fname += '.py'
        with open(fname, 'w') as f :
            f.write(self.get_iohelper_lines())
        return fname

    def select_n_events(self, n, random = True, key = 'EventStat') :
        if not self.lfns :
            return None
        if not self.lfns.values()[0].has_key(key) :
            self.get_bk_metadata()
        selected = {}
        nsel = 0
        if random :
            lfnList = self.lfn_list()
            rndm = TRandom3(0)
            while lfnList and nsel < n :
                i = int(rndm.Rndm() * len(lfnList))
                lfn = lfnList[i]
                selected[lfn] = self.lfns[lfn]
                nsel += self.lfns[lfn][key]
                lfnList.pop(i)
        else :
            for lfn, info in self.lfns.iteritems() :
                selected[lfn] = info
                nsel += info[key]
                if nsel > n :
                    break
        return LFNSet(selected)

    def get_active_replicas(self) :
        result = data_manager().getActiveReplicas(self.lfn_list())
        if not result['OK'] :
            return False
        result = data_manager().checkActiveReplicas(result['Value'])
        successful = result['Value']['Successful']
        for lfn, replicas in successful.iteritems() :
            self.lfns[lfn]['Replicas'] = replicas
        return True

    def gen_xml_catalog(self, fname = 'catalog.xml', site = '', depth=None, check=True,
                        ignoreMissing=False, verbose=False) :
        if check and (fname == self.catalogName) and os.path.exists(fname) :
            return fname
        if not self.lfns :
            return None
        if os.path.exists(fname) :
            os.remove(fname)
        cmdArgs = [#'lb-run', 'LHCbDirac', # Don't need this as Dirac env should be set up.
                   'dirac-bookkeeping-genXMLCatalog', 
                   '-l', ','.join(self.lfn_list()),
                   '--Catalog', fname]
        if None != depth :
            cmdArgs += ['--Depth', str(depth)]
        if site :
            cmdArgs += ['--Sites', site]
        if ignoreMissing :
            cmdArgs += ['--Ignore']
        if verbose :
            cmdArgs += ['-v']
        proc = subprocess.Popen(cmdArgs, stdout = subprocess.PIPE, stderr = subprocess.PIPE,
                                env = os.environ)
        # exit codes don't seem to be reliable.
        exitcode = proc.wait()
        if not os.path.exists(fname) :
            print 'Error generating xml catalog using:', ' '.join(cmdArgs)
            print 'exitcode:', exitcode
            print 'stdout:'
            print proc.stdout.read()
            print 'stderr:'
            print proc.stderr.read()
            fname = None
        proc.stdout.close()
        proc.stderr.close()
        self.catalogName = fname
        return fname

    def get_gaudipython_opts(self, extraopts = '') :
        inputtype = self.get_input_type()
        simulation, datatype = self.get_data_type()
        if not datatype :
            datatype = '2012'
        opts = self.get_iohelper_lines() + '''
from Configurables import DaVinci

dv = DaVinci()
dv.DataType = {0!r}
dv.Simulation = {1!r}
dv.InputType = {2!r}

import GaudiPython

# Initialize gaudi
gaudi = GaudiPython.AppMgr(outputlevel=3)
gaudi.HistogramPersistency = 'ROOT'

gaudi.initialize()

TES = gaudi.evtsvc()
'''.format(datatype, simulation, inputtype) + extraopts
        return opts 

    def run_gaudipython(self, extraopts = '', dvVersion = 'v36r7') :
        tempCatalog = False
        if not self.catalogName :
            tempCatalog = True
            if not self.gen_xml_catalog('_tmpcatalog.xml') :
                return None
        catalogName = self.gen_xml_catalog(self.catalogName)
        opts = self.get_gaudipython_opts(extraopts) 
        cmdArgs = ['lb-run', 'DaVinci', dvVersion, 'python', '-c', 
                   opts]
        proc = subprocess.Popen(cmdArgs, stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE, env = os.environ)
        exitcode = proc.wait()
        stdout = proc.stdout.readlines()
        stderr = proc.stderr.readlines()
        proc.stdout.close()
        proc.stderr.close()
        if tempCatalog :
            os.remove(catalogName)
            if os.path.exists(catalogName + '.temp') :
                os.remove(catalogName + '.temp')
            self.catalogName = None
        return {'proc' : proc, 'stdout' : stdout, 'stderr' : stderr}

    def get_rec_header(self, dvVersion = 'v36r7') :
        '''Extracts the Rec/Header from the files, including CondDB and DDDB tags.
        Currently just does the first event of the first file. Could
        try to update it to do all files, but not sure how just now.'''

        extraopts = '''
gaudi.run(1)
recHeader = TES['Rec/Header']
print '*** RECHEADER: {0!r}'.format(str(recHeader))
print '*** RECHEADER PARSED: {0}'.format(str(recHeader).replace('{ ', '{ "').replace(' :\\t', '" : "').replace('\\n', '", "').replace('" }', '}'))
'''
        output = self.run_gaudipython(extraopts=extraopts, dvVersion = dvVersion)
        rhLines = filter(lambda l : '*** RECHEADER PARSED' in l, output['stdout'])
        if not rhLines : 
            print 'stdout:'
            print ''.join(output['stdout'])
            print 'stderr:'
            print ''.join(output['stderr'])
            return False
        rhLines = rhLines[0].replace('*** RECHEADER PARSED:', '').split('}{')
        rh = eval(rhLines[0] + '}')
        rh.update(eval('{' + rhLines[1]))
        rh['condDBTags'] = dict(eval(rh['condDBTags'].replace('(', '("').replace(', ', '", "')\
                                         .replace(')', '")').replace('", "(', ', (')))
        for lfn in self.lfns.values() :
            lfn['RecHeader'] = rh
        return True

    def get_data_type(self) :
        if not self.lfns :
            return None, None
        dataTypes = (#('2008', ()),
                     #('2009', ()),
                     ('2010', ('/lhcb/LHCb/Collision10',)),
                     ('2011', ('/lhcb/LHCb/Collision11',)),
                     ('2012', ('/lhcb/LHCb/Collision12',)), 
                     ('2015', ('/lhcb/LHCb/Collision15',)),
                     ('2016', ('/lhcb/LHCb/Collision16',)),
                     (None, ('/LHCb/',)))
        mcTypes = (#('2008', ()),
                   #('2009', ('/lhcb/MC/',)),
                   ('MC09', ('/lhcb/MC/MC09',)),
                   ('2010', ('/lhcb/MC/MC10', '/lhcb/MC/2010')),
                   ('2011', ('/lhcb/MC/MC11a', '/lhcb/MC/2011')),
                   ('2012', ('/lhcb/MC/MC12', '/lhcb/MC/2012')), 
                   ('2015', ('/lhcb/MC/2015',)),
                   ('2016', ('/lhcb/MC/2016',)),
                   (None, ('/MC/',)))
        testLFN = self.lfns.keys()[0]
        for simulation, types in (False, dataTypes), (True, mcTypes) :
            for dataType, searches in types :
                if any(search in testLFN for search in searches) :
                    return simulation, dataType
        return None, None

    def get_tags(self) :
        if not self.lfns :
            return None
        if not self.lfns.values()[0].has_key('RecHeader') :
            self.get_rec_header()
        return self.lfns.values()[0]['RecHeader']['condDBTags']

    def get_input_type(self) :
        if not self.lfns :
            return None
        # DaVinci inputs = ('DST', 'DIGI', 'RDST', 'MDST', 'XDST', 'LDST')
        # Brunel inputs =  ['MDF', 'DST', 'XDST', 'DIGI']
        return self.lfns.keys()[0].split('.')[-1].upper()

    def get_app_config_opts(self, explicitTags = False) :
        if not self.lfns :
            return None
        opts = '''from Configurables import LHCbApp

app = LHCbApp()
'''
        simulation, dataType = self.get_data_type()
        opts += '''app.Simulation = {simulation!r}
app.DataType = {dataType!r}
'''.format(**locals())
        if simulation or explicitTags :
            tags = self.get_tags()
            if simulation :
                tags['LHCBCOND'] = tags['SIMCOND']
            opts += '''app.CondDBtag = {LHCBCOND!r}
app.DDDBtag = {DDDB!r}
'''.format(**tags)
        else :
            opts += '''
from Configurables import CondDB
CondDB().LatestGlobalTagByDataType = {dataType!r}
'''.format(**locals())
        inputType = self.get_input_type()
        opts += '''inputType = {inputType!r}
'''.format(**locals())
        return opts
        
class SortedLFNSets(object) :

    def __init__(self, lfnset, key, keyname) :
        self.keyname = keyname
        if isinstance(key, str) :
            self.key = lambda info : info[key]
        else :
            self.key = key
        self.lfnSets = {}
        for lfn, info in lfnset.lfns.iteritems() :
            keyVal = self.key(info)
            if self.lfnSets.has_key(keyVal) :
                # Should I make a copy of the info dict here, or retain the original ref?
                self.lfnSets[keyVal].lfns[lfn] = info
            else :
                self.lfnSets[keyVal] = LFNSet({lfn : info})

    def make_datafiles(self, fname) :
        if fname[-3:] == '.py' :
            fname = fname[:-3]
        fnames = []
        for keyVal, lfnSet in self.lfnSets.iteritems() :
            fnames.append(lfnSet.make_datafile(fname + '_' + self.keyname + '_' + str(keyVal) + '.py'))
        return fnames

def get_bk_metadata(lfn1, *lfns) :
    if isinstance(lfn1, dict) :
        for lfn in lfns :
            lfn1.update(lfn)
        return lfn1
    lfns = list((lfn1,) + lfns)
    res = bk_manager().getFileMetadata( lfns )
    if not res['OK'] : 
        print 'ERROR: Failed to get file metadata: %s' % res['Message']
        return None
    lfnMetadata = res['Value'].get( 'Successful', res['Value'] )
    return lfnMetadata

def split_by_key(key, lfn1, *lfns) :
    metadata = get_bk_metadata(lfn1, *lfns)
    if isinstance(key, str) :
        key = lambda info : info[key]
    keySorted = {}
    for lfn, info in metadata.iteritems() :
        keyVal = key(info)
        if keySorted.has_key(keyVal) :
            keySorted[keyVal][lfn] = info
        else :
            keySorted[keyVal] = {lfn : info}
    return keySorted

def make_datafile(fname, lfn1, *lfns) :
    if isinstance(lfn1, dict) :
        lfns = map(lambda lfn : 'LFN:' + lfn, lfn1)
    else :
        lfns = map(lambda lfn : 'LFN:' + lfn, (lfn1,) + lfns)
    with open(fname, 'w') as f :
        f.write('''
from Gaudi.Configuration import *
from GaudiConf import IOHelper
IOHelper('ROOT').inputFiles({0},
                            clear = True)
'''.format(repr(lfns).replace(',', ',\n')))

def make_split_datafiles(fname, key, keyName, lfn1, *lfns) :
    keySorted = split_by_key(key, lfn1, *lfns)
    if fname[-3:] == '.py' :
        fname = fname[:-3]
    fnames = []
    for keyVal, lfns in keySorted.iteritems() :
        keyFName = fname + '_' + keyName + '_' + str(keyVal) + '.py'
        make_datafile(keyFName, lfns)
        fnames.append(keyFName)
    return fnames

def get_run_info(fields, lfn1, *lfns) :
    metadata = get_bk_metadata(lfn1, *lfns)
    if isinstance(fields, str) :
        fields = [fields]
    for lfn, info in metadata.iteritems() :
        runNo = info['RunNumber']
        runInfo = bk_client().getRunInformation({'Fields' : fields, 'RunNumber' : runNo})['Value']
        info.update(runInfo[runNo])
    return metadata

def make_fill_split_datafiles(fname, lfn1, *lfns) :
    lfns = get_run_info('FillNumber', lfn1, *lfns)
    return make_split_datafiles(fname, 'FillNumber', 'FillNumber', lfns)

def get_lfns_from_bk_file(fname, nfiles = None) :
    lfns = []
    if None != nfiles :
        test = lambda : (len(lfns) < nfiles)
    else :
        test = lambda : True
    with open(fname) as f :
        for line in f :
            startNo = line.find('LFN:')
            if startNo == -1 :
                continue
            opener = line[startNo-1]
            line = line[startNo+4:]
            lfns.append(line[:line.find(opener)])
            if not test() :
                break
    return lfns

def make_fill_split_datafiles_from_bk_file(fname) :
    lfns = get_lfns_from_bk_file(fname)
    if not lfns :
        return None
    return make_fill_split_datafiles(fname, *lfns)

def get_active_replicas(lfn1, *lfns) :
    metadata = get_bk_metadata(lfn1, *lfns)
    res = data_manager().getActiveReplicas( list(metadata) )
    if not res['OK'] :
        return None
    res = data_manager().checkActiveReplicas( res['Value'] )
    successful = res['Value']['Successful']
    for lfn, replicas in successful.iteritems() :
        metadata[lfn]['Replicas'] = replicas
    return metadata

def make_5M_files() :
    for fname in glob.glob('*FillNumber*') :
        lfnSet = LFNSet(*get_lfns_from_bk_file(fname))
        lfnSet1M = lfnSet.select_n_events(5e6)
        print lfnSet1M.make_datafile(fname.replace('.py', '_5M.py'))

def make_10nb_files() :
    for fname in filter(lambda x : '5M' not in x, glob.glob('*FillNumber*')) :
        lfnSet = LFNSet(*get_lfns_from_bk_file(fname))
        lfnSubSet = lfnSet.select_n_events(1e4, key = 'Luminosity')
        print lfnSubSet.make_datafile(fname.replace('.py', '_10nb.py'))
        print 'nfiles', len(lfnSubSet.lfns), 'nevents', sum(info['EventStat'] for info in lfnSubSet.lfns.values()), 'lum', sum(info['Luminosity'] for info in lfnSubSet.lfns.values())
        
if __name__ == '__main__' :
    import os
    #for fname in os.listdir('.') :
    #fname = 'LHCb_Collision15em_Beam6500GeVVeloClosedMagUp_Real_Data_Reco15em_96000000_FULL.DST.py'
    #fname = 'LHCb_Collision15em_Beam6500GeVVeloClosedMagDown_Real_Data_Reco15em_96000000_FULL.DST.py'
    #make_fill_split_datafiles_from_bk_file(fname)
    lfn = '/lhcb/LHCb/Collision15em/FULL.DST/00046149/0000/00046149_00000002_1.full.dst'
    #value = get_active_replicas(lfn)
    #fname = os.environ['InputData'] + '/Collision15em/minbias/LHCb_Collision15em_Beam6500GeVVeloClosedMagDown_Real_Data_Reco15em_96000000_FULL.DST.py'
    #lfns = get_lfns_from_bk_file(fname)
    #metadata = get_active_replicas(*lfns) 
    #fnames = make_split_datafiles(fname, (lambda info : reduce(lambda x, y : x or 'CERN' in y, info['Replicas'].keys(), False)),
    #                              'CERNReplica', metadata)
    #lfns = LFNSet(lfn)
    #lfns.get_bk_metadata()
    #print lfns.lfns[lfn]
    lfnDuff = '/lhcb/LHCb/Collision15em/FULL.DST/00046149/0000/00046149_00005921_1.full.dst'
    lfnGood = '/lhcb/LHCb/Collision15em/FULL.DST/00046149/0001/00046149_00010223_1.full.dst'
    #lfnSet = LFNSet(lfnDuff, lfnGood)
    #lfnSet.get_bk_metadata()
    #print lfnSet.lfns
    #make_10nb_files()
    lfnSet = LFNSet('/lhcb/MC/2012/ALLSTREAMS.DST/00024857/0000/00024857_00000001_1.allstreams.dst')
    lfnSet.gen_xml_catalog('catalog.xml', verbose=True)
    #output = lfnSet.get_rec_header()
