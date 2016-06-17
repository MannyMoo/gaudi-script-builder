'''Annoyingly there seems to be no way to access the particle database
in the LHCb software without starting an LHCbApp and accessing the
particleSvc through it, so this packages it in a more portable format.'''

from EnvUtils import get_lhcb_env
from ParticleList import particlelist
import os

def update_particle_list() :
    lhcbenv = get_lhcb_env('LHCb')
    returnvals = lhcbenv.eval_python('''import PartProp.PartPropAlg
import PartProp.Service
from   GaudiPython.Bindings import AppMgr
from GaudiScriptBuilder.ParticleInfo import from_lhcb_property
gaudi = AppMgr()
gaudi.initialize()
pps   = gaudi.ppSvc()
particles = [from_lhcb_property(part) for part in pps.all()]
''', ('particles',), evalobjects = False, raiseerror = True)
    with open(os.path.join(os.environ['GAUDISCRIPTBUILDERROOT'], 'python',
                           'GaudiScriptBuilder', 'ParticleList.py'), 'w') as f :
        f.write('from GaudiScriptBuilder.ParticleInfo import ParticleInfo\n')
        f.write('particlelist = ' + returnvals['objects']['particles'] + '\n')

class ParticleDB(object) :
    __slots__ = ('particlelist',)

    def __init__(self, particlelist) :
        self.particlelist = list(particlelist)

    def find_particle(self, partid) :
        if isinstance(partid, int) :
            matches = filter(lambda part : (part.pdgid == partid), 
                             self.particlelist)
        else :
            matches = filter(lambda part : (part.name == partid),
                             self.particlelist)
        if matches :
            return matches[0]
        return None

particledb = ParticleDB(particlelist)
