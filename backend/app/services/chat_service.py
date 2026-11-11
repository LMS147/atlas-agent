"""Compatibility import. Implementation lives in backend.atlas.app.services.chat_service."""
import importlib
import sys

_module = importlib.import_module("backend.atlas.app.services.chat_service")
if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
