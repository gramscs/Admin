#!/usr/bin/env python3
"""Local runner that imports the project as package name 'app' and runs create_app().
This avoids needing the directory to be named 'app' on disk.
"""
import importlib.util
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Default to development for local runs before importing the app module.
# create_app() reads FLASK_ENV during import/bootstrap, so this must be set
# early to allow SQLite fallback when DATABASE_URL is not configured.
os.environ.setdefault("FLASK_ENV", "development")

spec = importlib.util.spec_from_file_location("app", str(ROOT / "__init__.py"))
app_module = importlib.util.module_from_spec(spec)
# Ensure the module is available as 'app' for absolute imports used in the codebase
sys.modules["app"] = app_module
spec.loader.exec_module(app_module)

create_app = getattr(app_module, "create_app")
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "").lower() != "production"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
