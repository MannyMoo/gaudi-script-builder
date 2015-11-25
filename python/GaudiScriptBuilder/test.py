from Configurables import TupleToolKinematic
from Configurables import TupleToolMCTruth
from Configurables import MCTupleToolPrompt
from Configurables import TupleToolTISTOS
from Configurables import TupleToolRecoStats
from Configurables import DaVinci
from Configurables import TupleToolGeometry
from DecayTreeTuple.Configuration import *
from Configurables import TupleToolStripping
from Configurables import TupleToolTrackInfo
from Configurables import TupleToolANNPID
from Configurables import TupleToolEventInfo
from Configurables import TupleToolMCBackgroundInfo
from Configurables import TupleToolPid
from Configurables import TupleToolPropertime
from Configurables import TupleToolPrimaries

TupleToolPropertime('Dst2010ToD0ToKpipiTuple.TupleToolPropertime')

TupleToolGeometry('Dst2010ToD0ToKpipiTuple.TupleToolGeometry')

TupleToolANNPID('Dst2010ToD0ToKpipiTuple.TupleToolANNPID')

TupleToolRecoStats('Dst2010ToD0ToKpipiTuple.TupleToolRecoStats')

TupleToolEventInfo('Dst2010ToD0ToKpipiTuple.TupleToolEventInfo')

TupleToolKinematic('Dst2010ToD0ToKpipiTuple.TupleToolKinematic')

TupleToolTrackInfo('Dst2010ToD0ToKpipiTuple.TupleToolTrackInfo')

MCTupleToolPrompt('mctt_prompt')

TupleToolMCTruth('Dst2010ToD0ToKpipiTuple.TupleToolMCTruth',
                 ToolList = ['MCTupleToolKinematic', 'MCTupleToolHierarchy'])
TupleToolMCTruth('Dst2010ToD0ToKpipiTuple.TupleToolMCTruth').addTupleTool(MCTupleToolPrompt('mctt_prompt'))

TupleToolMCBackgroundInfo('Dst2010ToD0ToKpipiTuple.TupleToolMCBackgroundInfo')

TupleToolPrimaries('Dst2010ToD0ToKpipiTuple.TupleToolPrimaries')

TupleToolPid('Dst2010ToD0ToKpipiTuple.TupleToolPid')

DecayTreeTuple('Dst2010ToD0ToKpipiTuple',
               Inputs = ['/Event/AllStreams/Phys/D2hhPromptDst2D2RSLine/Particles'],
               ToolList = [],
               Decay = '[D*(2010)+ -> ^(D0 -> ^K- ^pi+) ^pi+]CC')
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolPrimaries('Dst2010ToD0ToKpipiTuple.TupleToolPrimaries'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolPid('Dst2010ToD0ToKpipiTuple.TupleToolPid'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolGeometry('Dst2010ToD0ToKpipiTuple.TupleToolGeometry'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolANNPID('Dst2010ToD0ToKpipiTuple.TupleToolANNPID'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolMCBackgroundInfo('Dst2010ToD0ToKpipiTuple.TupleToolMCBackgroundInfo'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolMCTruth('Dst2010ToD0ToKpipiTuple.TupleToolMCTruth'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolRecoStats('Dst2010ToD0ToKpipiTuple.TupleToolRecoStats'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolTrackInfo('Dst2010ToD0ToKpipiTuple.TupleToolTrackInfo'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolPropertime('Dst2010ToD0ToKpipiTuple.TupleToolPropertime'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolKinematic('Dst2010ToD0ToKpipiTuple.TupleToolKinematic'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addTupleTool(TupleToolEventInfo('Dst2010ToD0ToKpipiTuple.TupleToolEventInfo'))

DecayTreeTuple('Dst2010ToD0ToKpipiTuple').addBranches({'lab0': '[D*(2010)+ -> (D0 -> K- pi+) pi+]CC'})

TupleToolTISTOS('Dst2010ToD0ToKpipiTuple.lab0_TupleToolTISTOS',
                Verbose = True,
                VerboseHlt1 = True,
                VerboseHlt2 = True,
                TriggerList = ['L0MuonDecision', 'L0DiMuonDecision', 'L0HadronDecision', 'L0MuonHighDecision', 'L0ElectronDecision', 'L0PhotonDecision', 'Hlt1SingleHadronDecision', 'Hlt1DiHadronDecision', 'Hlt1TrackAllL0Decision', 'Hlt1TrackMuonDecision', 'Hlt2Topo2BodySimpleDecision', 'Hlt2Topo3BodySimpleDecision', 'Hlt2Topo4BodySimpleDecision', 'Hlt2Topo2BodyBBDTDecision', 'Hlt2Topo3BodyBBDTDecision', 'Hlt2Topo4BodyBBDTDecision', 'Hlt2TopoMu2BodyBBDTDecision', 'Hlt2TopoMu3BodyBBDTDecision', 'Hlt2TopoMu4BodyBBDTDecision', 'Hlt2TopoE2BodyBBDTDecision', 'Hlt2TopoE3BodyBBDTDecision', 'Hlt2TopoE4BodyBBDTDecision', 'Hlt2TopoRad2BodyBBDTDecision', 'Hlt2TopoRad2plus1BodyBBDTDecision', 'Hlt2IncPhiDecision', 'Hlt2IncPhiSidebandsDecision'],
                VerboseL0 = True)

TupleToolStripping('Dst2010ToD0ToKpipiTuple.lab0_TupleToolStripping',
                   TriggerList = ['StrippingD2hhPromptDst2D2RSLineDecision'])

DecayTreeTuple('Dst2010ToD0ToKpipiTuple').lab0.ToolList = []

DecayTreeTuple('Dst2010ToD0ToKpipiTuple').lab0.addTupleTool(TupleToolStripping('Dst2010ToD0ToKpipiTuple.lab0_TupleToolStripping'))
DecayTreeTuple('Dst2010ToD0ToKpipiTuple').lab0.addTupleTool(TupleToolTISTOS('Dst2010ToD0ToKpipiTuple.lab0_TupleToolTISTOS'))

DaVinci('DaVinci',
        DataType = '2011',
        TupleFile = 'DVTuples.root',
        UserAlgorithms = [DecayTreeTuple('Dst2010ToD0ToKpipiTuple')],
        CondDBtag = 'Sim08-20130503-vc-md100',
        HistogramFile = 'DVHistos.root',
        Lumi = True,
        Simulation = True,
        DDDBtag = 'Sim08-20130503')

dv = DaVinci('DaVinci')

