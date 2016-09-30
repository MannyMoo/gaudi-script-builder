# For ppSvc decorator
import PartProp.PartPropAlg
import PartProp.Service

from GaudiPython.Bindings import AppMgr

started = False

def start_app_mgr() :
    gaudi = AppMgr()

    global started
    if not started :
        gaudi.initialize()
        started = True

    ppsvc   = gaudi.ppSvc()
    toolsvc = gaudi.toolSvc()
    evtsvc = tes = TES = gaudi.evtSvc()
    return locals()
