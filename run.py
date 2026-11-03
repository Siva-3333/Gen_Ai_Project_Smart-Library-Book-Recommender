"""Development entry point."""
import os
import sys

# Ensure root directory is in python search path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import importlib.util

app_path = os.path.join(root_dir, "app.py")
spec = importlib.util.spec_from_file_location("main_app", app_path)
main_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)

app = main_mod.app

if __name__ == "__main__":
    print("================================================================")
    print("  SMART LIBRARY BOOK RECOMMENDER - SERVER STARTING")
    print("  Localhost URL:     http://127.0.0.1:5000")
    print("  Network Wi-Fi URL: http://0.0.0.0:5000")
    print("================================================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
