from Configurables import CondDB
from DecayTreeTuple.Configuration import *
from Configurables import TrackScaleState
from Configurables import DaVinci
from Configurables import LHCbApp

CondDB('CondDB', LatestGlobalTagByDataType = '2015')
dv = DaVinci('DaVinci', UserAlgorithms = [TrackScaleState('TrackScaleState'), DecayTreeTuple('Dst2010ToD0ToKpipiTuple', Inputs = ['Hlt2CharmHadDstp2D0Pip_D02KmPip_LTUNBTurbo/Particles'], Decay = '[D*(2010)+ -> (D0 -> K- pi+) pi+]cc')], RootInTES = '/Event/Turbo', InputType = 'MDST')
app = LHCbApp('LHCbApp', DataType = '2015')
dtts = [DecayTreeTuple('Dst2010ToD0ToKpipiTuple', Inputs = ['Hlt2CharmHadDstp2D0Pip_D02KmPip_LTUNBTurbo/Particles'], Decay = '[D*(2010)+ -> (D0 -> K- pi+) pi+]cc')]
