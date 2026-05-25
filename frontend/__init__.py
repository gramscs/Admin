from flask import Blueprint

frontend_bp = Blueprint(
    "frontend",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)

from app.frontend.routes import main, pages, track  # noqa: E402,F401
