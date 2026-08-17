import sys
import os

_ROOT = os.path.join(os.path.dirname(__file__), "..")

# Ensure the project root is on the path for all tests
sys.path.insert(0, _ROOT)

# tools/ holds the build-time asset pipeline; it isn't a package
sys.path.insert(0, os.path.join(_ROOT, "tools"))
