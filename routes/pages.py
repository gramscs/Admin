from flask import Blueprint, render_template, abort
from app import cache
from jinja2.exceptions import TemplateNotFound
import logging

logger = logging.getLogger(__name__)

pages_bp = Blueprint("pages", __name__, template_folder="templates")


@pages_bp.route("/<page>")
@cache.cached(timeout=300)
def show_page(page):
    # Sanitize page name to prevent path traversal
    if not page or "/" in page or "\\" in page or ".." in page:
        logger.warning(f"Invalid page name attempted: {page}")
        abort(404)

    try:
        return render_template(f"pages/{page}.html")
    except TemplateNotFound:
        logger.warning(f"Template not found: pages/{page}.html")
        abort(404)
    except Exception as e:
        logger.error(f"Error rendering page {page}: {e}", exc_info=True)
        abort(500)
