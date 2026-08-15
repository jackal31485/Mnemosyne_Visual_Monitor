# Unit test for hermes_runtime import and snapshot
import sys
sys.path.insert(0,'src')
from discovery.hermes_runtime import HermesProfileInfo, HermesRuntimeSnapshot, get_hermes_runtime_snapshot

snap = get_hermes_runtime_snapshot()
print('executed', isinstance(snap, HermesRuntimeSnapshot))
