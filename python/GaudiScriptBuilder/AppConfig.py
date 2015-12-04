'''Tools for actually configuring Gaudi apps.'''

from GaudiKernel.Configurable import Configurable
from DecayTreeTuple.Configuration import *
import Configurables
import subprocess
from GaudiScriptBuilder.DecayDescriptors import *

def get_all_configurables(obj, recursive = True, top = True) :
    configurables = set()
    if isinstance(obj, Configurable) :
        configurables.add(obj)
        if recursive or top :
            for prop in obj.get_user_defined_properties().values() + obj.getTools() :
                configurables.update(get_all_configurables(prop, recursive = recursive, top = False))
    elif isinstance(obj, (tuple, list, set)) :
        for thing in obj :
            if isinstance(thing, Configurable) :
                configurables.update(thing.get_configurables(recursive = recursive, top = False))
    elif isinstance(obj, dict) :
        for thing in obj.values() :
            if isinstance(thing, Configurable) :
                configurables.update(thing.get_configurables(recursive = recursive, top = False))
    return configurables 

def get_all_import_lines(obj) :
    configurables = get_all_configurables(obj)
    importLines = set()
    for conf in configurables :
        importLines.add(conf.get_import_line())
    return importLines

def duck_punch_configurable() :
    def get_user_defined_properties(self) :
        #return self.getValuedProperties()
        props = self.properties()
        defaultProps = self.getDefaultProperties()
        return dict((attr, val) for attr, val in props.iteritems() \
                        if val != '<no value>' and val != defaultProps[attr])

    def get_import_line(self) :
        if hasattr(Configurables, self.__class__.__name__) :
            return 'from Configurables import ' + self.__class__.__name__ + '\n'
        return 'from ' + self.__module__ + ' import ' + self.__class__.__name__ + '\n'

    def get_configurables(self, recursive = True, top = True) :
        return get_all_configurables(self, recursive, top)

    def operate_configurables(self, opr, returnMethod = None) :
        configurables = self.get_configurables()
        returnVals = [opr(conf) for conf in configurables]
        if not returnMethod :
            return returnVals
        return returnMethod(returnVals)

    def get_import_lines(self) :
        return self.operate_configurables(lambda conf : conf.get_import_line(), set)

    def get_constructor_args(self) :
        props =  self.get_user_defined_properties()
        # For DecayTreeTuple and TupleTools - any tools that've been added
        # using addTupleTool will be done in the same way later.
        if props.has_key('ToolList') :
            toolNames = [tool.get_own_name() for tool in self.getTools()]
            props['ToolList'] = filter(lambda toolName : toolName.split('/')[-1] not in toolNames,
                                       props['ToolList'])
            #if len(props['ToolList']) == 0 :
            #    del props['ToolList']
        return props

    def to_string(self, ownVarName = None) :
        if not Configurable._reprTop and not Configurable._reprFull :
            return self.get_init_string()
        reprTopOrig = Configurable._reprTop
        # This isn't thread safe, but for generating scripts that shouldn't be
        # a problem. You can just use difference python instances if you want
        # to multi-task it. 
        if Configurable._reprTop and not Configurable._reprFull :
            Configurable._reprTop = False

        if not ownVarName :
            nameLen = len(self.__class__.__name__) + 1
            line = self.__class__.__name__ + '(' + repr(self.get_init_name())
            for attr, prop in self.get_constructor_args().iteritems() :
                line += ',\n' + (' ' * nameLen) + attr + ' = ' + repr(prop)
            line += ')'
        else :
            line = ''
            for attr, prop in self.get_constructor_args().iteritems() :
                line += ownVarName + '.' + attr + ' = ' + repr(prop) + '\n'
            
        if reprTopOrig and not Configurable._reprFull :
            Configurable._reprTop = True
        return line
            
    def __repr__(self) :
        return self.to_string()

    def get_own_name(self) :
        return self.getName().split('.')[-1]

    def get_init_name(self) :
        name = self.getName()
        splitName = name.split('.')
        if splitName[-1] != self.__class__.__name__ :
            return splitName[-1]
        if len(splitName) > 2 :
            return splitName[0] + '.' + '_'.join(splitName[1:])
        return name

    def get_init_string(self) :
        return self.__class__.__name__ + '(' + repr(self.get_init_name()) + ')'

    def get_configuration_lines(self, ownVarName = None) :
        lines = ''
        topConfigs = self.get_configurables(False) 
        for conf in topConfigs :
            if conf is self :
                continue 
            lines += conf.get_configuration_lines()
        lines += self.get_own_configuration_lines(ownVarName)
        return lines

    def get_tools_to_add(self) :
        return self.getTools()

    def get_own_configuration_lines(self, ownVarName = None) :
        lines = self.to_string(ownVarName) + '\n'
        if not ownVarName :
            ownVarName = self.get_init_string()
        for tool in self.get_tools_to_add() :
            if 'Tuple' in tool.__class__.__name__ :
                lines += ownVarName + '.addTupleTool(' \
                    + tool.get_init_string() + ')\n'
            else :
                lines += ownVarName + '.addTool(' + tool.get_init_string() + ')\n'
        lines += '\n'
        return lines

    def get_tool(self, name) :
        for tool in self.getTools() :
            if (name == tool.getName() or name == tool.get_own_name() 
                or name == tool.__class__.__name__) :
                return tool
        return None

    for attr, func in locals().iteritems() :
        setattr(Configurable, attr, func)
    Configurable._reprTop = True
    Configurable._reprFull = False

    def dtt_get_import_line(self) :
        return 'from DecayTreeTuple.Configuration import *\n'

    specialImports = {DecayTreeTuple : dtt_get_import_line}
    
    for cls, func in specialImports.iteritems() :
        cls.get_import_line = func

    # Special implementations for DecayTreeTuple

    def dtt_get_configurables(self, recursive = True, top = True) :
        confs = Configurable.get_configurables(self, recursive, top)
        # Exclude TupleToolDecay instances that represent branches
        # - they're treated separately.
        if hasattr(self, 'Branches') :
            branchNames = self.Branches.keys()
            confs = filter(lambda conf : conf.get_own_name() not in branchNames, confs)
        return confs
    
    def dtt_get_tools_to_add(self) :
        tools = self.getTools()
        if hasattr(self, 'Branches') :
            branchNames = self.Branches.keys()
            tools = filter(lambda tool : tool.get_own_name() not in branchNames, tools)
        return tools

    def dtt_get_own_configuration_lines(self, ownVarName = None) :
        lines = Configurable.get_own_configuration_lines(self, ownVarName)
        # Extra bits to configure branches.
        if hasattr(self, 'Branches') :
            lines += self.get_init_string() + '.addBranches({0!r})\n\n'.format(self.Branches)
            branchNames = self.Branches.keys()
            branchConfigs = [getattr(self, branchName) for branchName in branchNames]
            for branch in branchConfigs :
                initName = self.get_init_string() + '.' + branch.get_own_name()
                lines += branch.get_configuration_lines(initName)

        return lines

    def dtt_get_constructor_args(self) :
        props = Configurable.get_constructor_args(self)
        if props.has_key('Branches') :
            del props['Branches']
        return props

    DecayTreeTuple.get_configurables = dtt_get_configurables
    DecayTreeTuple.get_tools_to_add = dtt_get_tools_to_add
    DecayTreeTuple.get_own_configuration_lines = dtt_get_own_configuration_lines
    DecayTreeTuple.get_constructor_args = dtt_get_constructor_args

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

def is_trigger(version) :
    return isinstance(version, int) or '0x' in version

def get_line_opts(dataopts, version, linename) :
    isTrigger = is_trigger(version)
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
            imports.update(get_all_import_lines(obj))
            lines.append(obj.get_configuration_lines())
        for key, obj in self.namedObjs.iteritems() :
            imports.update(get_all_import_lines(obj))
            lines.append(obj.get_configuration_lines())
            objline = obj.get_init_string()
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
                             "TupleToolANNPID",
                             "TupleToolTrackInfo",
                             "TupleToolRecoStats",],
                 mcToolList = ['TupleToolMCTruth',
                               'TupleToolMCBackgroundInfo'],
                 L0List = [],
                 HLT1List = [],
                 HLT2List = [],
                 strippingList = [],
                 headBranchName = 'lab0') :
        from Configurables import GaudiSequencer, DaVinci, TupleToolStripping, \
            TupleToolTrigger
    
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

        isTrigger = is_trigger(version)
        if isTrigger :
            if not linename in HLT2List :
                HLT2List.append(linename)
        else :
            if not linename in strippingList :
                strippingList.append(linename)
        for trigList in L0List, HLT1List, HLT2List, strippingList :
            for i, trig in enumerate(trigList) :
                if trig[-8:] != 'Decision' :
                    trigList[i] += 'Decision'

        dtts = []
        for desc in decayDescs :
            dtt = DecayTreeTuple(descriptor_to_name(desc) + 'Tuple',
                                 ToolList = [])
            dtts.append(dtt)
            dtt.Decay = add_carets(desc)
            dtt.Inputs = [inputLocation]
            for tool in toolList :
                dtt.addTupleTool(tool)

            dtt.addBranches({headBranchName : desc})
            headBranch = getattr(dtt, headBranchName)

            if not isTrigger :
                ttstrip = dtt.addTupleTool('TupleToolStripping')
                ttstrip.TriggerList = [linename + 'Decision'] + strippingList
                ttstrip.VerboseStripping = True
                
                # This doesn't currently work. There doesn't seem to be an easy way
                # to TISTOS stripping lines currently, which is infuriating. Surely everyone
                # needs to do this for MC studies? It might be possible to do it using 
                # TESTisTos in a Bender algorithm.
                #ttstriptistos = headBranch.addTupleTool('TupleToolTISTOS/tistos_stripping')
                #ttstriptistos.TriggerTisTosName = 'TESTisTos'
                #ttstriptistos.TriggerList = [os.path.join(rootInTES, inputLocation)]

            if dv.getProp('Simulation') :
                for tool in mcToolList :
                    dtt.addTupleTool(tool)

            if L0List or HLT1List or HLT2List or strippingList :
                ttrig = headBranch.addTupleTool('TupleToolTISTOS')
                ttrig.TriggerList = L0List + HLT1List + HLT2List + strippingList
                ttrig.Verbose = True
                ttrig.VerboseL0 = True
                ttrig.VerboseHlt1 = True
                ttrig.VerboseHlt2 = True
                ttrig.VerboseStripping = True
            dv.UserAlgorithms.append(dtt)

        objs = []
        if locals().has_key('CondDB') :
            objs.append(CondDB())
        objsdict = {'dv' : dv}

        Script.__init__(self, fname, objs, objsdict)
        
if __name__ == '__main__' :

    from Configurables import TupleToolStripping
    
    datafile = '/afs/cern.ch/work/m/malexand//charm/2011/data/mc/MC_2011_27163003_Beam3500GeV2011MagDownNu2Pythia8_Sim08a_Digi13_Trig0x40760037_Reco14a_Stripping20r1NoPrescalingFlagged_ALLSTREAMS.DST.py'
    opts = DaVinciScript('test.py', '20r1', 'StrippingD2hhPromptDst2D2RSLine',
                         datafile, 
                         L0List = ['L0' + t for t in ['Muon',
                                                      'DiMuon',
                                                      'Hadron',
                                                      'MuonHigh',
                                                      'Electron',
                                                      'Photon'
                                                      ]],
                         HLT1List = ['Hlt1SingleHadron',
                                     'Hlt1DiHadron',
                                     'Hlt1TrackAllL0',
                                     'Hlt1TrackMuon'],
                         HLT2List = ['Hlt2Topo2BodySimple',
                                     'Hlt2Topo3BodySimple',
                                     'Hlt2Topo4BodySimple',
                                     'Hlt2Topo2BodyBBDT',
                                     'Hlt2Topo3BodyBBDT',
                                     'Hlt2Topo4BodyBBDT',
                                     'Hlt2TopoMu2BodyBBDT',
                                     'Hlt2TopoMu3BodyBBDT',
                                     'Hlt2TopoMu4BodyBBDT',
                                     'Hlt2TopoE2BodyBBDT',
                                     'Hlt2TopoE3BodyBBDT',
                                     'Hlt2TopoE4BodyBBDT',
                                     'Hlt2TopoRad2BodyBBDT',
                                     'Hlt2TopoRad2plus1BodyBBDT',
                                     'Hlt2IncPhi',
                                     'Hlt2IncPhiSidebands'])

    dtt = opts.namedObjs['dv'].UserAlgorithms[0]

    ttmc = dtt.get_tool('TupleToolMCTruth')
    #ttmc.ToolList += ['MCTupleToolPrompt']
    from Configurables import MCTupleToolPrompt
    ttmc.addTupleTool(MCTupleToolPrompt('mctt_prompt'))
    ttmc.ToolList += ['MCTupleToolHierarchy']

    opts.write()
