'''Stripping utils.

Requires the DaVinci environment.

What we want to do:

Give the script a stripping version, line name and input data, and get a script to
produce an ntuple.

To run on stripped data:
- Get decay descriptor and output location to configure DecayTreeTuple.
- Configure DaVinci appropriately for the input data:
 - Data type.
 - Is simulation.
 - Tags.
 - RootInTes if mdst (requires line info, could be done via LHCbApp) - can this be set at the 
   sequencer level now?
- Rerun stripping line sequence if necessary.
 - For MC optionally removing selection criteria and adding truth matching to inputs. 
'''

from StrippingConf.Configuration import StrippingConf, StrippingStream
import StrippingArchive, StrippingSettings
from StrippingSettings.Utils import strippingConfiguration
from StrippingArchive.Utils import buildStreams
from StrippingArchive import strippingArchive
import re, os
from Configurables import GaudiSequencer, CombineParticles
try :
    from collections import OrderedDict
except :
    from ordereddict import OrderedDict
from GaudiScriptBuilder.DecayDescriptors import *
from GaudiScriptBuilder.LineConfigBase import LineConfigBase

def prepend_stripping(name) :
    if name[:len('Stripping')] != 'Stripping' :
        return 'Stripping' + name
    return name

def append_line(name) :
    if name[-len('Line'):] != 'Line' :
        return name + 'Line'
    return name

def expand_sequence(seq) :
    if isinstance(seq, GaudiSequencer) :
        return expand_sequence(seq.Members)
    if isinstance(seq, (tuple, list)) :
        members = []
        for thing in seq :
            members += expand_sequence(thing)
        return members
    return [seq]

def available_stripping_versions() :
    return filter(lambda x : 'Stripping' in x, dir(StrippingArchive))

class StrippingConfig(object) :
    '''Access the configuration of a given stripping version and the streams and 
    lines it contains.'''
    __slots__ = ('config', 'archive', 'streams', 'version')
    
    def __init__(self, version) :
        self.version = prepend_stripping(version)
        self.config  = strippingConfiguration(self.version)
        self.archive = strippingArchive(self.version)
        self.streams = buildStreams(stripping=self.config, archive=self.archive) 

    def get_stream(self, name) :
        for stream in self.streams :
            if stream.name() == name :
                return stream
        return None

    def find_streams(self, expr) :
        matches = []
        for stream in self.streams :
            if re.search(expr, stream.name()) :
                matches.append(stream)
        return matches

    def get_line(self, name) :
        name = prepend_stripping(append_line(name))
        for stream in self.streams :
            for line in stream.lines :
                if line.name() == name :
                    return StrippingLineConfig(stream, line)
        return None

    def find_lines(self, expr) :
        matches = []
        for stream in self.streams :
            for line in stream.lines :
                if re.search(expr, line.name()) :
                    matches.append(StrippingLineConfig(stream, line))
        return matches 


class StrippingLineConfig(LineConfigBase) :
    '''Access info on a specific stripping line and the stream that contains it, 
    particularly: the output location, root in TES, and decay descriptors, 
    which are needed to configure a DaVinci job. Decay descriptor parsing is
    still pretty crude.'''

    __slots__ = ('stream', 'line', 'expandedMembers')

    def __init__(self, stream, line) :
        self.stream = stream
        self.line = line
        self.expandedMembers = expand_sequence(self.line._members)
        
    def members(self) :
        return self.line._members

    def root_in_tes(self, simulation = False) :
        if not simulation :
            return '/Event/' + self.stream.name()
        return '/Event/AllStreams'

    def output_location(self) :
        return self.line.outputLocation()

    def decay_descriptors(self) :
        descs = OrderedDict()
        '''This won't work in all situations, eg if you have the same head particle as input to 
        the next combined particle (something like Upsilon -> D0 D0bar), but it works with most.'''

        for comb in filter(lambda x : isinstance(x, CombineParticles), self.expandedMembers) :
            if hasattr(comb, 'DecayDescriptor') and comb.DecayDescriptor :
                head, strippeddesc = head_descriptor(comb.DecayDescriptor)
                if descs.has_key(head) :
                    descs[head].append(comb.DecayDescriptor)
                else :
                    descs[head] = [comb.DecayDescriptor]
            else :
                for desc in comb.DecayDescriptors :
                    head, strippeddesc = head_descriptor(desc)
                    if descs.has_key(head) :
                        descs[head].append(desc)
                    else :
                        descs[head] = [desc]
        return descs

    def line_name(self) :
        return self.line.name()

    def stream_name(self) :
        return self.stream.name()


if '__main__' == __name__ :
    
    #version = '21r1'
    version = '20'
    streams = StrippingConfig(version)
    lines = streams.find_lines('D02HHHH')

    l = lines[0]
    print l.full_decay_descriptor()
