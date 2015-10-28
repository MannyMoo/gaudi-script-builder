from DecayTreeTuple.Configuration import *
from Configurables import DaVinci

dtt = DecayTreeTuple('Dst2010ToD0ToKpipiTuple', Inputs = ['/Event/AllStreams/Phys/D2hhPromptDst2D2RSLine/Particles'], Decay = '[D*(2010)+ -> (D0 -> K- pi+) pi+]CC')
dv = DaVinci('DaVinci', DataType = '2011', TupleFile = 'DVTuples.root', HistogramFile = 'DVHistos.root', UserAlgorithms = [dtt], Lumi = True, DDDBtag = 'Sim08-20130503', CondDBtag = 'Sim08-20130503-vc-md100', Simulation = True)
