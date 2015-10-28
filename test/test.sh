#!/bin/bash

scriptbuilder.py --datafile /afs/cern.ch/work/m/malexand//charm/2011/data/mc/MC_2011_27163003_Beam3500GeV2011MagDownNu2Pythia8_Sim08a_Digi13_Trig0x40760037_Reco14a_Stripping20r1NoPrescalingFlagged_ALLSTREAMS.DST.py --linename StrippingD2hhPromptDst2D2RSLine --version 20r1 --outputfile test-stripping.py > stdout-stripping 2> stderr-stripping

#scriptbuilder.py --datafile /afs/cern.ch/work/m/malexand/charm/baryon-lifetimes-2015/data/LHCb_Collision15_Beam6500GeVVeloClosedMagDown_Real_Data_Turbo01_94000000_TURBO.MDST.py --linename Hlt2CharmHadDstp2D0Pip_D02KmPip_LTUNBTurbo --version "0x01080050" --outputfile test-turbo.py > stdout-trigger 2> stderr-trigger
