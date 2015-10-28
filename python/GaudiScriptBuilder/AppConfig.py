'''Tools for actually configuring Gaudi apps.'''

from GaudiKernel.Configurable import Configurable
from DecayTreeTuple.Configuration import *
import Configurables
import subprocess
from GaudiScriptBuilder.DecayDescriptors import *

def get_all_configurables(obj) :
    configurables = set()
    if isinstance(obj, Configurable) :
        configurables.add(obj)
        for attr, prop in obj.get_user_defined_properties().iteritems() :
            configurables.update(get_all_configurables(prop))
    elif isinstance(obj, (tuple, list, set)) :
        for thing in obj :
            if isinstance(thing, Configurable) :
                configurables.update(thing.get_configurables())
    elif isinstance(obj, dict) :
        for thing in obj.values() :
            if isinstance(thing, Configurable) :
                configurables.update(thing.get_configurables())
    return configurables 

def get_all_import_lines(obj) :
    configurables = get_all_configurables(obj)
    importLines = set()
    for conf in configurables :
        importLines.add(conf.get_import_line())
    return importLines

def duck_punch_configurable() :
    def get_user_defined_properties(self) :
        props = self.properties()
        defaultProps = self.getDefaultProperties()
        return dict((attr, val) for attr, val in props.iteritems() \
                        if val != '<no value>' and val != defaultProps[attr])

    def get_import_line(self) :
        if hasattr(Configurables, self.__class__.__name__) :
            return 'from Configurables import ' + self.__class__.__name__ + '\n'
        return 'from ' + self.__module__ + ' import ' + self.__class__.__name__ + '\n'

    def get_configurables(self) :
        return get_all_configurables(self)

    def operate_configurables(self, opr, returnMethod = None) :
        configurables = self.get_configurables()
        returnVals = [opr(conf) for conf in configurables]
        if not returnMethod :
            return returnVals
        return returnMethod(returnVals)

    def get_import_lines(self) :
        return self.operate_configurables(lambda conf : conf.get_import_line(), set)

    def __repr__(self) :
        line = self.__class__.__name__ + '(' + repr(self.getName())
        for attr, prop in self.get_user_defined_properties().iteritems() :
            line += ', ' + attr + ' = ' + repr(prop)
        line += ')'
        return line

    for attr, func in locals().iteritems() :
        setattr(Configurable, attr, func)

    def dtt_get_import_line(self) :
        return 'from DecayTreeTuple.Configuration import *\n'

    specialImports = {DecayTreeTuple : dtt_get_import_line}
    
    for cls, func in specialImports.iteritems() :
        cls.get_import_line = func

duck_punch_configurable()

def get_data_opts(datafile, explicitTags = False) :
    dataopts = '''from GaudiScriptBuilder.LFNUtils import LFNSet, get_lfns_from_bk_file

lfns = LFNSet(get_lfns_from_bk_file({datafile!r})[0])
print '***'
print lfns.get_app_config_opts({explicitTags!r})
print '***'
'''.format(**locals())
    args = ['lb-run', 'LHCbDirac', 'python', '-c', dataopts]
    proc = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    proc.wait()
    stdoutLines = proc.stdout.readlines()
    stderrLines = proc.stderr.read()
    proc.stdout.close()
    proc.stderr.close()
    #print stdoutLines
    try :
        startLine = stdoutLines.index('***\n')+1
        endLine = startLine + stdoutLines[startLine:].index('***\n')
        return ''.join(stdoutLines[startLine:endLine])
    except :
        print 'stdout:'
        print ''.join(stdoutLines)
        print 
        print 'stderr:'
        print stderrLines
        raise

def get_line_opts(dataopts, version, linename) :
    isTrigger = isinstance(version, int) or '0x' in version
    opts = dataopts 
    opts += '''version = {0!r}
linename = {1!r}
'''.format(version, linename)

    if isTrigger :
        opts += '''from GaudiScriptBuilder.Trigger import TriggerConfig
config = TriggerConfig(version) 
'''
    else :
        opts += '''from GaudiScriptBuilder.Stripping import StrippingConfig
config = StrippingConfig(version)
'''
    opts += '''line = config.find_lines(linename)[0]
rootInTES, inputLocation = line.root_in_tes_and_output_location((inputType == 'MDST'),
                                                                app.Simulation)
decayDescs = line.full_decay_descriptors()
'''
    try :
        exec opts
        return {'rootInTES' : rootInTES, 'inputLocation' : inputLocation, 'decayDescs' : decayDescs}
    except :
        opts += '''print '***'
print repr({'rootInTES' : rootInTES, 'inputLocation' : inputLocation, 'decayDescs' : decayDescs})
'''
        args = ['lb-run']
        if isTrigger :
            args.append('Moore')
        else :
            args.append('DaVinci')
        args += ['python', '-c', opts]
        proc = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        proc.wait()
        stdoutLines = proc.stdout.readlines()
        stderrLines = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
        try :
            iStart = stdoutLines.index('***\n')
            return eval(stdoutLines[iStart+1])
        except :
            print 'stdout:'
            print ''.join(stdoutLines)
            print
            print 'stderr:'
            print stderrLines
            raise

class Script(object) :
    __slots__ = ('fname', 'objs', 'namedObjs') 
    
    def __init__(self, fname, objs, namedObjs) :
        self.fname = fname
        self.objs = objs
        self.namedObjs = namedObjs

    def get_opts(self) :
        imports = set()
        lines = []
        for obj in self.objs :
            objline = repr(obj)
            imports.update(get_all_import_lines(obj))
            lines.append(objline + '\n\n')
        for key, obj in self.namedObjs.iteritems() :
            objline = repr(obj)
            imports.update(get_all_import_lines(obj))
            lines.append(key + ' = ' + objline + '\n\n')
        return ''.join(list(imports) + ['\n'] + lines)

    def write(self) :
        with open(self.fname, 'w') as f :
            f.write(self.get_opts())
        return self.fname

class DaVinciScript(Script) :
    
    def __init__(self, fname, version, linename, datafile, explicitTags = False,
                 useTrackScaleState = True, 
                 toolList = ["TupleToolPropertime",
                             "TupleToolKinematic",
                             "TupleToolGeometry",
                             "TupleToolEventInfo",
                             "TupleToolPrimaries",
                             "TupleToolPid",
                             "TupleToolTrackInfo",
                             "TupleToolRecoStats",]) :
        from Configurables import GaudiSequencer, DaVinci
    
        # Defines Simulation, CondDBtag, DDDBtag, inputType
        dataopts = get_data_opts(datafile, explicitTags)
        exec dataopts

        # Defines rootInTES, inputLocation, and decayDescs
        lineOpts = get_line_opts(dataopts, version, linename)
        for key, val in lineOpts.iteritems() :
            exec key + ' = ' + repr(val)

        dv = DaVinci()
        dv.InputType = inputType
        dv.RootInTES = rootInTES
        dv.TupleFile = 'DVTuples.root'
        dv.HistogramFile = 'DVHistos.root'
        dv.Lumi = True
        for attr, val in app.get_user_defined_properties().iteritems() :
            setattr(dv, attr, val)
        # Make sure DataType is set, in case it's the default value.
        dv.DataType = app.DataType

        # Can't use TrackScaleState for 2015 data yet as it's not been calibrated.
        if not app.Simulation and dv.DataType != '2015' and useTrackScaleState :
            from Configurables import TrackScaleState
            dv.UserAlgorithms.append(TrackScaleState())

        dtts = []
        for desc in decayDescs :
            dtt = DecayTreeTuple(descriptor_to_name(desc) + 'Tuple')
            dtts.append(dtt)
            dtt.Decay = add_carets(desc)
            dtt.Inputs = [inputLocation]
            dtt.ToolList = [
                #"TupleToolTISTOS",
                #"TupleToolTrigger",
                "TupleToolPropertime",
                "TupleToolKinematic",
                "TupleToolGeometry",
                "TupleToolEventInfo",
                "TupleToolPrimaries",
                "TupleToolPid",
                "TupleToolTrackInfo",
                "TupleToolRecoStats",
                ]
            if dv.getProp('Simulation') :
                dtt.ToolList += ['TupleToolMCTruth',
                                 'TupleToolMCBackgroundInfo']
            dv.UserAlgorithms.append(dtt)
        objs = []
        if locals().has_key('CondDB') :
            objs.append(CondDB())
        objsdict = {'dv' : dv}
        if len(dtts) == 1 :
            objsdict['dtt'] = dtts[0]
        else :
            objsdict['dtts'] = dtts
        Script.__init__(self, fname, objs, objsdict)
        
if __name__ == '__main__' :

    datafile = '/afs/cern.ch/work/m/malexand//charm/2011/data/mc/MC_2011_27163003_Beam3500GeV2011MagDownNu2Pythia8_Sim08a_Digi13_Trig0x40760037_Reco14a_Stripping20r1NoPrescalingFlagged_ALLSTREAMS.DST.py'
    opts = DaVinciScript('test.py', '20r1', 'StrippingD2hhPromptDst2D2RSLine',
                         datafile)
    opts.write()
