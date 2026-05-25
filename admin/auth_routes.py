"""Canonical admin authentication routes."""

import logging

from flask import redirect, render_template, request, url_for

from app import limiter
from app.admin import admin_bp
from app.admin.auth import (
    check_admin_credentials,
    is_admin_authenticated,
    login_admin,
    logout_admin,
)

logger = logging.getLogger(__name__)


@admin_bp.route("/admin/login", methods=["GET"])
def login():
    """Render the admin login form."""
    if is_admin_authenticated():
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html", error=None)


@admin_bp.route("/admin/login", methods=["POST"])
@limiter.limit("5 per minute")
def login_submit():
    """Process the admin login form."""
    if is_admin_authenticated():
        return redirect(url_for("admin.dashboard"))

    error = None

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if check_admin_credentials(username, password):
        login_admin(username=username)
        logger.info("Admin login successful for user: %s", username)
        return redirect(url_for("admin.dashboard"))

    logger.warning("Failed admin login attempt for username: %s", username)
    error = "Invalid username or password."

    return render_template("admin/login.html", error=error)


@admin_bp.route("/admin/logout", methods=["GET"])
@limiter.limit("10 per minute")
def logout():
    """Clear admin session and redirect to the login page."""
    logout_admin()
    logger.info("Admin logged out.")
    return redirect(url_for("admin.login"))
