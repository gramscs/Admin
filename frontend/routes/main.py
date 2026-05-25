import logging
import requests
from flask import render_template, request, redirect, url_for, flash, current_app

from app import cache, limiter
from app.frontend import frontend_bp

logger = logging.getLogger(__name__)


@frontend_bp.route("/")
@cache.cached(timeout=300)
def index():
    return render_template("main/index.html")


@frontend_bp.route("/about")
@cache.cached(timeout=300)
def about():
    return render_template("main/about.html")


@frontend_bp.route("/contact", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def contact():
    if request.method == "POST":
        source = request.form.get("source", "").strip().lower()
        return_to_homepage = source == "homepage"

        def _redirect_after_submit():
            if return_to_homepage:
                return redirect(url_for("frontend.index") + "#contact")
            return redirect(url_for("frontend.contact"))

        payload = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "subject": request.form.get("subject", "").strip(),
            "message": request.form.get("message", "").strip(),
        }

        try:
            api_url = url_for("public_api.submit_contact", _external=True)
            response = requests.post(api_url, json=payload, timeout=10)
            body = response.json()

            if response.ok and body.get("success"):
                flash("Message sent successfully! We'll get back to you soon.", "success")
                return _redirect_after_submit()

            flash(body.get("message", "There was an issue submitting your message. Please try again."), "error")
            if return_to_homepage:
                return _redirect_after_submit()
            return render_template("main/contact.html")
        except Exception as exc:
            logger.error("Unexpected error in contact form: %s", exc)
            flash("An unexpected error occurred. Please try again later.", "error")
            if return_to_homepage:
                return redirect(url_for("frontend.index") + "#contact")
            return render_template("main/contact.html")

    return render_template("main/contact.html")
