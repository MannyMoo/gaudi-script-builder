from Configurables import DaVinci, GaudiSequencer, TupleToolStripping, \
    CombineParticles, FilterDesktop, TupleToolDecayTreeFitter, SubstitutePID, \
    TrackScaleState, TisTosParticleTagger, LoKi__Hybrid__TupleTool

from DecayTreeTuple.Configuration import *
from Gaudi.Configuration import FileCatalog

try :
    import MakeTuple
except ImportError :
    import sys
    sys.path.append('/afs/cern.ch/work/m/malexand/charm/baryon-lifetimes/ganga-scripts/')
    import MakeTuple

from MakeTuple import *

strippingVersion = 'Stripping20r1'

toolList = [
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
    #"TupleToolGeneration"
    ]

streams = get_streams(strippingVersion)


dtt = DecayTreeTuple('Dst2010ToD0ToKpipiTuple', Inputs = ['/Event/AllStreams/Phys/D2hhPromptDst2D2RSLine/Particles'], Decay = '[D*(2010)+ -> (D0 -> K- pi+) pi+]CC')
ttmc = dtt.addTupleTool('TupleToolMCTruth')
ttmc.ToolList += ['MCTupleToolPrompt']
ttmc.ToolList += ['MCTupleToolHierarchy']
dtt.ToolList += ['TupleToolMCTruth',
                 #'TupleToolGeneration'
                 'TupleToolMCBackgroundInfo'
                 ]
dtfVars = {
    # Index 0 for CHILDFUN meas the particle itself, so 1 is the D0.
    "DTF_M_D0_BPVIPCHI2"  : "DTF_FUN(CHILDFUN(BPVIPCHI2(), 1), False, 'D0')"
    }

decayDesc = dtt.Decay.replace('^', '')
dtt.addBranches({'Dst' : decayDesc})
dstLoKiTuple = LoKi__Hybrid__TupleTool('DstLoKiTuple')
dstLoKiTuple.Variables = dtfVars
dtt.Dst.ToolList += [ "LoKi::Hybrid::TupleTool/DstLoKiTuple" ]
dtt.Dst.addTool(dstLoKiTuple)
dtt.Dst.InheritTools = True

dv = DaVinci('DaVinci', DataType = '2011', TupleFile = 'DVTuples.root', HistogramFile = 'DVHistos.root', UserAlgorithms = [dtt], Lumi = True, DDDBtag = 'Sim08-20130503', CondDBtag = 'Sim08-20130503-vc-md100', Simulation = True)

FileCatalog().Catalogs = ["xmlcatalog_file:/afs/cern.ch/work/m/malexand//charm/2011/data/mc/pool_xml_catalog.xml"]

dv.EvtMax = 1000

