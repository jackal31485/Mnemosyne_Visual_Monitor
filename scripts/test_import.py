import sys
sys.path.append('src')
from discovery.hermes_runtime import HermesProfileInfo, HermesRuntimeSnapshot, get_hermes_runtime_snapshot
print('imports ok', type(HermesProfileInfo), type(HermesRuntimeSnapshot))
snap = get_hermes_runtime_snapshot()
print('snapshot', snap)
