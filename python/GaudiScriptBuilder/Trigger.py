'''Trigger utils.

Requires the Moore environment.

What we want to do:
- Provide the name of a turbo trigger line (and possibly a TCK, Moore version or run period) and obtain:
 - Its output location.
 - Its sequence.
 - Its decay descriptor. 
In order to configure DaVinci and DecayTreeTuple to obtain an ntuple.
'''

# less $MOOREROOT/../../../../HLT/HLT_v24r2/Hlt/TCKUtils/python/TCKUtils/utils.py
from TCKUtils import utils as tckutils
import re, os
from collections import OrderedDict
from GaudiScriptBuilder.DecayDescriptors import *
from GaudiScriptBuilder.LineConfigBase import LineConfigBase

def int_tck(tck) :
    if isinstance(tck, str) :
        return int(tck, 16)
    return tck

def get_properties(tck, name, attr = '') :
    if not attr :
        return tckutils.getProperties(tck, name).values()[0]
    attrs = attr.split('.')
    if len(attrs) == 1 :
        return get_properties(tck, name)[attr]
    for attr in attrs :
        props = get_properties(tck, name)
        if not props.has_key(attr) or not props[attr] :
            return None
        name = props[attr]
    return props[attr]

class TriggerConfig(object) :
    __slots__ = ('tck',)

    def __init__(self, tck) :
        self.tck = int_tck(tck)

    def get_hlt2_lines(self) :
        '''This can take a while the first time it's called.'''
        return tckutils.getHlt2Lines(self.tck)
        
    def find_lines(self, expr) :
        matches = filter(lambda line : re.search(expr, line), self.get_hlt2_lines())
        return [TriggerLineConfig(self.tck, match) for match in matches]

class TriggerLineConfig(LineConfigBase) :
    __slots__ = ('tck', 'name')

    def __init__(self, tck, name) :
        self.tck = int_tck(tck)
        self.name = name

    def line_name(self) :
        return self.name.split('/')[-1]

    def root_in_tes(self, simulation = False) :
        if not simulation :
            return '/Event/Turbo'
        return '/Event/AllStreams'

    def output_location(self) :
        return os.path.join(self.line_name(), 'Particles')

    def get_properties(self, name = '', attr = '') :
        return get_properties(self.tck, (self.name if not name else name), attr)

    def get_filter_sequence(self) :
        seq = []
        filter0Members = self.get_properties(attr = 'Filter0.Members')
        if filter0Members :
            seq += eval(filter0Members)
        filter1Members = self.get_properties(attr = 'Filter1.Members')
        if filter1Members :
            seq += eval(filter1Members)
        return seq

    def get_decay_descriptors(self) :
        seq = filter(lambda alg : 'CombineParticles' in alg, self.get_filter_sequence())
        alldescs = OrderedDict()
        for alg in seq :
            props = self.get_properties(alg)
            if props['DecayDescriptor'] :
                descs = [props['DecayDescriptor']]
            else :
                descs = eval(props['DecayDescriptors'])
            for desc in descs :
                head, strippeddesc = head_descriptor(desc)
                if alldescs.has_key(head) :
                    alldescs[head].append(strippeddesc)
                else :
                    alldescs[head] = [desc]
        return alldescs
        
    def full_decay_descriptors(self) :
        return full_decay_descriptors(self.get_decay_descriptors())

if __name__ == '__main__' : 
    versions = sorted(tckutils.getReleases())
    hlttypes = dict((version, filter(lambda x : 'Physics' in x, tckutils.getHltTypes(version))) for version in versions)
    version = 'MOORE_v24r2'
    tcks = tckutils.getTCKs(version, hlttypes[version][0])
    hltConf = TriggerConfig(tcks[-1][0])
    line = hltConf.find_hlt2_lines('Hlt2CharmHadDstp2D0Pip_D02KmPip_LTUNBTurbo')[0]
    print line.get_decay_descriptors()
    descs = line.get_full_decay_descriptors()
    print descs
