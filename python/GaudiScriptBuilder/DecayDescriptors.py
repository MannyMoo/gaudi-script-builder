'''Decay descriptor manipulation is pretty crude. Probably be better writing a
dedicated class to handle it, but it'll do for now.'''

import re

def strip_descriptor(desc) :
    '''This is particularly crude as some particles have brackets in their names,
    like D*(2010)+, and others have cc in their names, like Xicc.'''
    for c in '[', ']', '(', ')', 'cc', 'CC' :
        desc = desc.replace(c, '')
    return desc

def head_descriptor(desc) :
    desc = strip_descriptor(desc)
    return desc.split()[0], desc

def full_decay_descriptor(stages) :
    desc = stages[-1]
    '''Possibly need to deal better with intermediate cc's rather than just stripping them away ...'''
    for nextdesc in stages[-2::-1] :
        head, strippeddesc = head_descriptor(nextdesc)
        desc = desc.replace(head, '(' + strippeddesc + ')')
    return desc

def full_decay_descriptors(alldescs) :
    counts = [0 for i in xrange(len(alldescs))]
    lens = [len(descs) for head, descs in alldescs.iteritems()]
    heads = alldescs.keys()
    fulldescs = []
    while counts[0] < lens[0] :
        stages = [alldescs[head][counts[i]] for i, head in enumerate(heads)]
        fulldescs.append(full_decay_descriptor(stages))
        counts[-1] += 1
        for i in xrange(len(counts)-1, 0, -1) :
            if counts[i] == lens[i] :
                counts[i] = 0
                counts[i-1] += 1
    return set(desc.replace(']cc', ']CC') for desc in fulldescs)

def descriptor_to_name(desc) :
    subs = (('->', 'To'), 
            ('*', 'st'), 
            ('(', ''), 
            (')', ''),
            ('[', ''),
            (']', ''),
            ('cc', ''),
            ('CC', ''),
            ('+', ''),
            ('-', ''),
            (' ', ''))
    return reduce(lambda desc, sub : desc.replace(*sub), subs, desc)

def add_carets(decay) :
    return re.sub(' ([(A-Za-z])', ' ^\\1', decay)
