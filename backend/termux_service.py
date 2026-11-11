"""Compatibility entry point for backend.server.termux_service."""
import importlib
import sys

_module = importlib.import_module("backend.server.termux_service")
if __name__ == "__main__":
    raise SystemExit(_module.main())
else:
    sys.modules[__name__] = _module
