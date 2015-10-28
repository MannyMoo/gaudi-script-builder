
from GaudiScriptBuilder.DecayDescriptors import *
import os

class LineConfigBase(object) :
    __slots__ = ()
    
    def root_in_tes_and_output_location(self, mdst = False, simulation = False) :
        rootInTES = self.root_in_tes(simulation)
        outputLoc = self.output_location()
        if mdst :
            return rootInTES, outputLoc
        return '', os.path.join(rootInTES, outputLoc)

    def full_decay_descriptors(self) :
        '''Not fool-proof to use the decay descriptors like this, but works for most cases.
        Would need to properly work out all the independent paths to the final output in the 
        member sequence and how they fit together. But this will work for now.'''

        return full_decay_descriptors(self.decay_descriptors())

