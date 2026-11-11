"""Compatibility import. Implementation lives in backend.atlas.telegram.bot."""
import importlib
import sys

_module = importlib.import_module("backend.atlas.telegram.bot")
if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
