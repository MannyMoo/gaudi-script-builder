'''Tools for actually configuring Gaudi apps.'''

from GaudiKernel.Configurable import Configurable
from DecayTreeTuple.Configuration import *
import Configurables
import subprocess
from GaudiScriptBuilder.DecayDescriptors import *
import EnvUtils 
from Configurables import DaVinci, LHCbApp, CondDB, SubstitutePID, CombineParticles, \
    FilterDesktop, GaudiSequencer, DaVinci__N3BodyDecays, DaVinci__N4BodyDecays,\
    DaVinci__N5BodyDecays, DaVinci__N6BodyDecays

from PhysSelPython.Wrappers import Selection, SelectionSequence
#from GaudiConfUtils import configurableExists
import StandardParticles
#from GaudiKernel.Configurable import Configurable

def is_trigger(version) :
    return isinstance(version, int) or '0x' in version

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

mcbasicinputs = {'K+' : StandardParticles.StdAllNoPIDsKaons,
                 'pi+' : StandardParticles.StdAllNoPIDsPions,
                 'mu-' : StandardParticles.StdAllNoPIDsMuons,
                 'p+' : StandardParticles.StdAllNoPIDsProtons,
                 'e-' : StandardParticles.StdAllNoPIDsElectrons}

selections = {}

def build_mc_unbiased_selection(decayDesc, arrow = '==>') :
    preamble = [ "from LoKiPhysMC.decorators import *" , "from LoKiPhysMC.functions import mcMatch" ]
    decayDesc.set_carets(False)
    decayDescCC = decayDesc.copy()
    decayDescCC.cc = True
    algname = decayDesc.get_full_alias() + '_MCSel'
    if algname in selections :
        return selections[algname]
    if not decayDesc.daughters :
        alg = FilterDesktop(algname + '_Filter')
        if decayDesc.particle.name in mcbasicinputs :
            inputsel = mcbasicinputs[decayDesc.particle.name]
        else :
            conj = decayDesc.conjugate()
            if conj.particle.name in mcbasicinputs :
                inputsel = mcbasicinputs[conj.particle.name]
            else :
                raise ValueError("Can't find MC basic input for particle " + repr(decayDesc.particle.name))
        alg.Code = 'mcMatch({0!r})'.format(decayDescCC.to_string(arrow))
        alg.Preambulo = preamble
        sel = Selection(algname,
                        Algorithm = alg,
                        RequiredSelections = [inputsel])
        selections[algname] = sel
        return sel
    inputs = []
    daughtercuts = {}
    for daughter in decayDescCC.daughters :
        originaldaughtercc = daughter.cc
        daughter.cc = True
        sel = build_mc_unbiased_selection(daughter, arrow)
        daughter.cc = originaldaughtercc
        inputs.append(sel)
        #daughter.caret = True
        #daughtercuts[daughter.particle.name] = 'mcMatch({0!r})'.format(decayDescCC.to_string(arrow))
        #daughter.caret = False
    #comb = nCombiners[len(decayDesc.daughters)](algname + '_Comb')
    comb = CombineParticles(algname + '_Comb')
    # CombineParticles uses small cc, so set ishead = False
    comb.DecayDescriptors = [decayDesc.to_string(depth = 1, ishead = False)]
    comb.MotherCut = 'mcMatch({0!r})'.format(decayDescCC.to_string(arrow))
    comb.Preambulo = preamble
    comb.DaughtersCuts = daughtercuts
    sel = Selection(algname,
                    Algorithm = comb,
                    RequiredSelections = inputs)
    selections[algname] = sel
    return sel

def duck_punch_configurable() :
    def get_user_defined_properties(self) :
        #return self.getValuedProperties()
        props = self.properties()
        defaultProps = self.getDefaultProperties()
        return dict((attr, val) for attr, val in props.iteritems() \
                        if not (val == '<no value>' or val == defaultProps[attr]
                                or repr(val) == repr(defaultProps[attr])))

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

def duck_punch_dtt() :
    # Special implementations for DecayTreeTuple

    def get_import_line(self) :
        return 'from DecayTreeTuple.Configuration import *\n'


    def get_configurables(self, recursive = True, top = True) :
        confs = Configurable.get_configurables(self, recursive, top)
        # Exclude TupleToolDecay instances that represent branches
        # - they're treated separately.
        if hasattr(self, 'Branches') :
            branchNames = self.Branches.keys()
            confs = filter(lambda conf : conf.get_own_name() not in branchNames, confs)
        return confs
    
    def get_tools_to_add(self) :
        tools = self.getTools()
        if hasattr(self, 'Branches') :
            branchNames = self.Branches.keys()
            tools = filter(lambda tool : tool.get_own_name() not in branchNames, tools)
        return tools

    def get_own_configuration_lines(self, ownVarName = None) :
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

    def get_constructor_args(self) :
        props = Configurable.get_constructor_args(self)
        if props.has_key('Branches') :
            del props['Branches']
        return props

    def configure_tools(self, toolList = ["TupleToolPropertime",
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
                        headBranch = None) :

        for trigList in L0List, HLT1List, HLT2List, strippingList :
            for i, trig in enumerate(trigList) :
                if trig[-8:] != 'Decision' :
                    trigList[i] += 'Decision'

        for tool in toolList + mcToolList :
            self.addTupleTool(tool)

        if strippingList :
            ttstrip = self.addTupleTool('TupleToolStripping')
            ttstrip.TriggerList = strippingList
            ttstrip.VerboseStripping = True
            
            # This doesn't currently work. There doesn't seem to be an easy way
            # to TISTOS stripping lines currently, which is infuriating. Surely everyone
            # needs to do this for MC studies? It might be possible to do it using 
            # TESTisTos in a Bender algorithm, or INTES functor.
            #ttstriptistos = headBranch.addTupleTool('TupleToolTISTOS/tistos_stripping')
            #ttstriptistos.TriggerTisTosName = 'TESTisTos'
            #ttstriptistos.TriggerList = [os.path.join(rootInTES, inputLocation)]

        if L0List or HLT1List or HLT2List :
            if headBranch == None :
                headBranch = self
            ttrig = headBranch.addTupleTool('TupleToolTISTOS')
            # TupleToolTISTOS can't do stripping this way either.
            ttrig.TriggerList = L0List + HLT1List + HLT2List 
            ttrig.Verbose = True
            ttrig.VerboseL0 = True
            ttrig.VerboseHlt1 = True
            ttrig.VerboseHlt2 = True

    def configure_for_line(self, decaydesc, inputloc, linename, version,
                           simulation,
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
                           strippingList = []) :

        
        
        self.Decay = decaydesc.to_string(carets = True)
        self.Inputs = [inputloc]
        isTrigger = is_trigger(version)
        if isTrigger :
            self.WriteP2PVRelations = False
            # Not sure if this is necessary since RootInTES will be set for turbo data.
            #self.InputPrimaryVertices = '/Event/Turbo/Primary'
            if not linename in HLT2List :
                HLT2List.append(linename)
        else :
            if not linename in strippingList :
                strippingList.append(linename)

        self.addBranches(decaydesc.branches())
        headBranch = getattr(self, decaydesc.get_alias())

        self.configure_tools(toolList = toolList,
                             mcToolList = mcToolList,
                             L0List = L0List,
                             HLT1List = HLT1List,
                             HLT2List = HLT2List,
                             strippingList = strippingList,
                             headBranch = headBranch)

    for name, val in locals().iteritems() :
        setattr(DecayTreeTuple, name, val)

            
duck_punch_configurable()
duck_punch_dtt()

def duck_punch_davinci() :

    def get_data_settings(self, datafile, explicitTags = False) :
        diracenv = EnvUtils.get_lhcb_env('LHCbDirac')
        opts = '''from GaudiScriptBuilder.LFNUtils import LFNSet, get_lfns_from_bk_file

lfns = LFNSet(get_lfns_from_bk_file({datafile!r})[0])
InputType = lfns.get_input_type()
Simulation, DataType = lfns.get_data_type()
'''.format(datafile = datafile)
        attrs = 'InputType', 'Simulation', 'DataType'
        returnvals = diracenv.eval_python(opts, attrs, raiseerror = True)

        if returnvals['objects']['Simulation'] or explicitTags :
            opts = '''from GaudiScriptBuilder.LFNUtils import LFNSet, get_lfns_from_bk_file

lfns = LFNSet(get_lfns_from_bk_file({datafile!r}, 1)[0])
tags = lfns.get_tags()
if 'SIMCOND' in tags :
    CondDBtag = tags['SIMCOND']
else :
    CondDBtag = tags['LHCBCOND']
DDDBtag = tags['DDDB']
'''.format(datafile = datafile)
            tagvals = diracenv.eval_python(opts, ('CondDBtag', 'DDDBtag'), raiseerror = True)
            returnvals['objects'].update(tagvals['objects'])
        return returnvals['objects']
    
    def configure_data_opts(self, datafile, explicitTags = False) :
        if not isinstance(datafile, dict) :
            settings = self.get_data_settings(datafile, explicitTags)
        else :
            settings = datafile

        if not 'CondDBtag' in settings :
            conddb = CondDB()
            conddb.LatestGlobalTagByDataType = settings['DataType']
            self.extraobjs.add(conddb)
        
        for attr, val in settings.iteritems() :
            if hasattr(self.__class__, attr) :
                setattr(self, attr, val)

    def get_line_settings(self, linename, version) :
        isTrigger = is_trigger(version)
        opts = '''version = {0!r}
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
rootInTES, inputLocation = line.root_in_tes_and_output_location({0!r},
                                                                {1!r})
decayDescs = line.full_decay_descriptors()
'''.format(self.getProp('InputType') == 'MDST',
           self.getProp('Simulation'))

        if isTrigger :
            env = EnvUtils.get_lhcb_env('Moore')
        else :
            env = EnvUtils.get_stripping_env(version)

        returnVals = env.eval_python(opts, ('rootInTES', 'inputLocation', 'decayDescs'),
                                     raiseerror = True)

        self.RootInTES = returnVals['objects']['rootInTES']
        if isTrigger :
            from Configurables import DstConf
            dstconf = DstConf()
            dstconf.Turbo = True
            self.extraobjs.add(dstconf)
        objs = returnVals['objects']
        objs['decayDescs'] = list(objs['decayDescs'])
        objs['linename'] = linename
        objs['version'] = version
        for i, desc in enumerate(objs['decayDescs']) :
            objs['decayDescs'][i] = parse_decay_descriptor(desc)
        return objs

    def add_line_tuple_sequence(self, linesettings,
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
                                aliases = {},
                                labXAliases = False,
                                substitutions = {}) :
        if not isinstance(linesettings, dict) :
            linesettings = self.get_line_settings(*linesettings)
        rootInTES = linesettings['rootInTES']
        linename = linesettings['linename']
        version = linesettings['version']
        decayDescs = linesettings['decayDescs']
        inputlocation = linesettings['inputLocation']
        if self.getProp('Simulation') :
            rootInTES = '/'.join(rootInTES.split('/')[:-1] + ['AllStreams'])
        if self.getProp('InputType').lower() != 'mdst' :
            inputlocation = os.path.join(rootInTES, inputlocation)
            rootInTES = ''
        self.RootInTES = rootInTES
        lineseq = GaudiSequencer(linename + '-Sequence')
        if substitutions :
            subs = {}
            for i, desc in enumerate(decayDescs) :
                descsubs, newdesc = desc.get_substitutions(substitutions)
                subs.update(descsubs)
                decayDescs[i] = newdesc
            newinputlocation = inputlocation.split('/')
            newinputlocation[-2] += '-SubPID'
            newinputlocation = '/'.join(newinputlocation)
            subpid = SubstitutePID(linename + '-SubPID',
                                   Code = 'ALL', 
                                   Substitutions = subs,
                                   Inputs = [inputlocation],
                                   Output = newinputlocation)
            lineseq.Members += [subpid]
            inputlocation = newinputlocation
        for desc in decayDescs :
            if labXAliases :
                desc.set_labX_aliases()
            elif aliases :
                desc.set_aliases(aliases)
            desctuple = DecayTreeTuple(desc.get_full_alias() + 'Tuple',
                                       ToolList = [])
            desctuple.configure_for_line(desc, inputlocation,
                                         linename, version, 
                                         self.getProp('Simulation'),
                                         toolList, mcToolList, L0List, HLT1List, HLT2List,
                                         strippingList)
            lineseq.Members.append(desctuple)
        self.UserAlgorithms.append(lineseq)
        return linesettings, lineseq

    def add_TrackScaleState(self, pos = 0) :
        if not self.getProp('Simulation') :
            from Configurables import TrackScaleState
            self.UserAlgorithms.insert(pos, TrackScaleState(RootInTES = self.getProp('RootInTES')))

    
    def make_script(self, fname) :
        return Script(fname, self.extraobjs, {'dv' : self})

    def write_script(self, fname) :
        self.make_script(fname).write()

    def add_mc_unbiased_sequence(self, decayDesc, arrow = '==>',
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
                                 strippingList = []) :
        sel = build_mc_unbiased_selection(decayDesc, arrow)
        selseq = SelectionSequence(decayDesc.get_full_alias() + '_MCSeq',
                                   TopSelection = sel)
        seq = selseq.sequence()
        dtt = DecayTreeTuple(decayDesc.get_full_alias() + '_MCTuple',
                             Decay = decayDesc.to_string(carets = True),
                             Inputs = [sel.outputLocation()], 
                             ToolList = [])
        dtt.addBranches(decayDesc.branches())
        headBranch = getattr(dtt, decayDesc.get_alias())

        dtt.configure_tools(toolList = toolList,
                            mcToolList = mcToolList,
                            L0List = L0List,
                            HLT1List = HLT1List,
                            HLT2List = HLT2List,
                            strippingList = strippingList,
                            headBranch = headBranch)
        seq.Members.append(dtt)
        self.UserAlgorithms.append(seq)
        return seq

    extraobjs = set()

    for name, val in locals().iteritems() :
        setattr(DaVinci, name, val)


duck_punch_davinci()

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
    
        # Defines Simulation, CondDBtag, DDDBtag, InputType, DataType
        dv = DaVinci()
        dv.configure_data_opts(datafile, explicitTags)

        dv.TupleFile = 'DVTuples.root'
        dv.HistogramFile = 'DVHistos.root'
        dv.Lumi = True

        # Can't use TrackScaleState for 2015 data yet as it's not been calibrated.
        if useTrackScaleState :
            dv.add_TrackScaleState()

        # Defines rootInTES, inputLocation, and decayDescs
        dv.add_line_tuple_sequence(linename, version, 
                                   toolList, mcToolList,
                                   L0List, HLT1List, HLT2List, strippingList,
                                   headBranchName)

        objsdict = {'dv' : dv}

        Script.__init__(self, fname, dv.extraobjs, objsdict)
        
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
