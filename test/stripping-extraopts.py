from Gaudi.Configuration import FileCatalog
from Configurables import LoKi__Hybrid__TupleTool

FileCatalog().Catalogs = ["xmlcatalog_file:/afs/cern.ch/work/m/malexand//charm/2011/data/mc/pool_xml_catalog.xml"]

dv.EvtMax = 1000

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
