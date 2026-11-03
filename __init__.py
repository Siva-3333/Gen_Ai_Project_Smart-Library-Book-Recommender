"""Legacy app package redirection to root app.py."""
import os
import importlib.util

root_app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))
spec = importlib.util.spec_from_file_location("root_app", root_app_path)
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)

create_app = _mod.create_app
app = _mod.app
