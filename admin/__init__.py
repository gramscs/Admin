from importlib import import_module

from flask import Blueprint, redirect, url_for, current_app

admin_bp = Blueprint("admin", __name__)


def _register_route_modules():
    """Import route modules for blueprint registration side effects."""
    import_module("app.admin.auth_routes")


_register_route_modules()


@admin_bp.route("/admin/dashboard", methods=["GET"])
def dashboard():
    """Compatibility route: serve the Flask-Admin index at `/admin/dashboard`.

    Instead of a redirect (which would change the browser URL to `/flask-admin/`),
    invoke the Flask-Admin index view function directly and return its response
    so the client remains on `/admin/dashboard` (tests expect this URL).
    """
    view = current_app.view_functions.get("flask_admin.index")
    if view:
        return view()

    # Fallback to a redirect if the Flask-Admin index isn't available for some reason.
    return redirect(url_for("flask_admin.index"))


@admin_bp.route("/admin/consignments", methods=["GET"])
def consignments():
    """Compatibility route: serve the Flask-Admin consignments list at `/admin/consignments`.

    This mirrors the behavior for `/admin/dashboard` and allows legacy links
    and tests to visit `/admin/consignments` while the real admin view is
    registered under `consignments_admin.index_view`.
    """
    # Redirect to the Flask-Admin managed consignments view. Rendering the
    # view function in-place can cause Flask-Admin's internal URL building to
    # resolve relative endpoints incorrectly, so use a redirect which preserves
    # Flask-Admin's expected endpoint context.
    return redirect(url_for("consignments_admin.index_view"))
