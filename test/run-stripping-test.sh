cat test-stripping.py > _test-stripping.py
cat stripping-extraopts.py >> _test-stripping.py

gaudirun.py _test-stripping.py /afs/cern.ch/work/m/malexand//charm/2011/data/mc/MC_2011_27163003_Beam3500GeV2011MagDownNu2Pythia8_Sim08a_Digi13_Trig0x40760037_Reco14a_Stripping20r1NoPrescalingFlagged_ALLSTREAMS.DST.py >& stdout-stripping-test