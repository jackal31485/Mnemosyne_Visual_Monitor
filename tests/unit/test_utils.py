# Utility test for executable lookup
import sys, shutil
sys.path.insert(0,'src')
from discovery.utils import run_command

def test_executable_lookup():
    exe = shutil.which('python3')
    assert exe is not None
