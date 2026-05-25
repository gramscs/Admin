import logging
import re
from flask import render_template, request, redirect

from app.frontend import frontend_bp
from app.api.public import lookup_consignment

logger = logging.getLogger(__name__)
CONSIGNMENT_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9]{1,16}$")


@frontend_bp.route("/track", methods=["GET", "POST"])
def track_page():
    consignment = None
    error_message = None

    if request.method == "POST":
        number = (request.form.get("consignment_number") or "").strip().upper()
        if not number:
            error_message = "Please enter a consignment number."
        elif not CONSIGNMENT_NUMBER_PATTERN.fullmatch(number):
            error_message = "Invalid consignment number format."
        else:
            consignment = lookup_consignment(number)
            if not consignment:
                error_message = "Consignment not found. Please check the number and try again."

    return render_template("track/track.html", consignment=consignment, error_message=error_message)


@frontend_bp.route("/track/pod/<consignment_number>", methods=["GET"])
def consignment_pod(consignment_number):
    return redirect(f"/api/public/pod/{consignment_number}")
