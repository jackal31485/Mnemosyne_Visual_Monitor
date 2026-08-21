import pathlib, sys
# Ensure src directory is on PYTHONPATH when running tests
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
src_dir = PROJECT_ROOT/"src"
sys.path.insert(0, str(src_dir))
