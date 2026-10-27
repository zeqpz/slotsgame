"""runbuild.py boy|skull [--fast] [--clips-only]: build_rig.main(); FH=<seconds> dumps the stack if it hangs."""
import faulthandler, sys, os
if os.environ.get('FH'):
    faulthandler.dump_traceback_later(int(os.environ['FH']), exit=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_rig
build_rig.main()
