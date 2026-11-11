"""Compatibility entry point for backend.server.healthcheck."""
import importlib
import sys

_module = importlib.import_module("backend.server.healthcheck")
if __name__ == "__main__":
    raise SystemExit(_module.main())
else:
    sys.modules[__name__] = _module
