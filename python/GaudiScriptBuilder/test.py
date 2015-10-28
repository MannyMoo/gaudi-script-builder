from DecayTreeTuple.Configuration import *
from Configurables import DaVinci
from Configurables import GaudiSequencer

dv = DaVinci('DaVinci', UserAlgorithms = [GaudiSequencer('spamseq', Members = [DecayTreeTuple('spam')])])
dtt = DecayTreeTuple('spam')
