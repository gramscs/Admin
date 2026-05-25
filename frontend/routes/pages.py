import logging
from flask import render_template, abort
from jinja2.exceptions import TemplateNotFound

from app import cache
from app.frontend import frontend_bp

logger = logging.getLogger(__name__)


@frontend_bp.route("/<page>")
@cache.cached(timeout=300)
def show_page(page):
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
