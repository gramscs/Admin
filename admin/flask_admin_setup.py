import io as _io
import logging
import os
import uuid

from flask import current_app, flash, redirect, request, send_file, url_for
from flask_admin import Admin, AdminIndexView, BaseView, expose
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import secure_filename

from app.admin.auth import is_admin_authenticated
from app.controllers import build_backup_payload
from app.controllers.responses import json_error, json_success
from app.db.session import transaction
from app.models import Consignment, Lead, db
from app.services.consignment_importer import (
    export_rows_to_workbook_bytes,
    import_from_workbook,
)
from app.services.logistics import (
    normalize_consignment_number,
    normalize_indian_pincode,
    normalize_status,
)
from app.services.pdf_export import generate_consignment_pdf
from app.services.pod_storage import (
    get_pod_url as _get_pod_url,
    get_supabase_client as _get_supabase_client,
)

logger = logging.getLogger(__name__)


class SecureModelView(ModelView):
    can_view_details = True
    page_size = 50

    def is_accessible(self):
        return is_admin_authenticated()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin.login", next=request.url))


class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return is_admin_authenticated()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin.login", next=request.url))

    @expose("/")
    def index(self):
        stats = {
            "consignments": Consignment.query.count(),
            "leads": Lead.query.count(),
            "consignments_url": url_for("consignments_admin.index_view"),
            "leads_url": url_for("leads_admin.index_view"),
            "backup_url": url_for("backup_admin.download"),
        }
        return self.render("flask_admin/dashboard.html", stats=stats)


class ConsignmentAdminView(SecureModelView):
    column_list = (
        "id",
        "consignment_number",
        "status",
        "pickup_pincode",
        "pickup_address",
        "pickup_tag",
        "pickup_date",
        "drop_pincode",
        "drop_address",
        "drop_tag",
        "drop_date",
        "eta",
        "pod_image",
    )
    column_editable_list = (
        "status",
        "pickup_pincode",
        "drop_pincode",
        "pickup_date",
        "drop_date",
        "eta",
        "pickup_address",
        "drop_address",
        "pickup_tag",
        "drop_tag",
    )
    column_searchable_list = (
        "consignment_number",
        "status",
        "pickup_tag",
        "drop_tag",
        "pickup_pincode",
        "drop_pincode",
        "pickup_address",
        "drop_address",
    )
    column_filters = (
        "status",
        "pickup_pincode",
        "drop_pincode",
        "pickup_date",
        "drop_date",
    )
    form_excluded_columns = ("eta_debug_json",)
    can_export = True
    export_types = ["csv"]
    page_size = 50
    list_template = "flask_admin/consignments_list.html"

    @expose("/export.xlsx")
    def export_xlsx(self):
        rows = Consignment.query.order_by(Consignment.id.asc()).all()
        output = export_rows_to_workbook_bytes(rows)
        return send_file(
            output,
            as_attachment=True,
            download_name="consignments.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @expose("/export.pdf")
    def export_pdf(self):
        rows = Consignment.query.order_by(Consignment.id.asc()).all()
        output = generate_consignment_pdf(rows)
        return send_file(
            output,
            as_attachment=True,
            download_name="consignments.pdf",
            mimetype="application/pdf",
        )

    @expose("/import", methods=["POST"])
    def import_xlsx(self):
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("Please choose an Excel file (.xlsx).", "danger")
            return redirect(url_for("consignments_admin.index_view"))

        filename = upload.filename.lower()
        if not filename.endswith(".xlsx"):
            flash("Only .xlsx files are supported.", "danger")
            return redirect(url_for("consignments_admin.index_view"))

        try:
            added_count, skipped_count = import_from_workbook(
                upload,
                Consignment=Consignment,
                db=db,
                normalize_consignment_number=normalize_consignment_number,
                normalize_status=normalize_status,
                normalize_indian_pincode=normalize_indian_pincode,
            )
            flash(
                f"Import completed. Added: {added_count}, skipped duplicates: {skipped_count}.",
                "success",
            )
        except ValueError as error:
            try:
                db.session.rollback()
            except Exception:
                logger.exception("Failed to rollback DB session after import error")
            flash(str(error), "danger")
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                logger.exception(
                    "Failed to rollback DB session after unexpected import error"
                )
            logger.exception("Unexpected error in Excel import")
            flash("Failed to import Excel file.", "danger")

        return redirect(url_for("consignments_admin.index_view"))

    @action("set_delivered", "Mark as Delivered", "Mark selected consignments delivered?")
    def action_set_delivered(self, ids):
        try:
            updated = (
                Consignment.query.filter(Consignment.id.in_(ids))
                .update({Consignment.status: "Delivered"}, synchronize_session=False)
            )
            db.session.commit()
            flash(f"Updated {updated} consignments to Delivered.", "success")
        except Exception:
            db.session.rollback()
            flash("Bulk status update failed.", "danger")


class LeadAdminView(SecureModelView):
    can_create = False
    can_edit = False
    can_delete = True
    column_list = ("id", "name", "email", "phone", "subject", "message", "created_at")
    column_searchable_list = ("name", "email", "phone", "subject")
    column_default_sort = ("created_at", True)

    @action(
        "reject_blank_phone",
        "Reject blank-phone leads",
        "Delete all selected leads with no phone number?",
    )
    def action_reject_blank_phone(self, ids):
        Lead.query.filter(Lead.id.in_(ids), (Lead.phone.is_(None)) | (Lead.phone == "")).delete(
            synchronize_session=False
        )
        db.session.commit()
        flash("Blank-phone leads deleted.")


class BackupView(BaseView):
    @expose("/", methods=["GET"])
    @expose("/download", methods=["GET"])
    def download(self):
        table_specs = [
            ("consignments", Consignment, {"eta_debug_json"}),
            ("leads", Lead, set()),
        ]
        buffer, metadata = build_backup_payload(table_specs)
        filename = f"backup_{metadata['generated_at'].replace(':', '').replace('-', '').replace('T', '_')}.json"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/json",
        )

    def is_accessible(self):
        return is_admin_authenticated()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin.login"))


def init_flask_admin(app):
    """Initialize Flask-Admin views bound to SQLAlchemy models."""
    admin = Admin(
        app,
        name="Admin Panel",
        url="/flask-admin",
        endpoint="flask_admin",
        index_view=SecureAdminIndexView(url="/flask-admin", endpoint="flask_admin"),
    )

    admin.add_view(
        ConsignmentAdminView(
            Consignment,
            db.session,
            name="Consignments",
            endpoint="consignments_admin",
            category="Operations",
        )
    )

    admin.add_view(
        LeadAdminView(
            Lead,
            db.session,
            name="Leads",
            endpoint="leads_admin",
            category="CRM",
        )
    )

    admin.add_view(
        BackupView(name="Download Backup", endpoint="backup_admin", category="System")
    )

    return admin
