"""Compatibility import. Implementation lives in backend.atlas.app.repositories.sessions."""
import importlib
import sys

_module = importlib.import_module("backend.atlas.app.repositories.sessions")
if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
