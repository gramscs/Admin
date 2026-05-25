import io
import logging
import warnings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"reportlab\.lib\.rl_safe_eval",
)

logger = logging.getLogger(__name__)


def generate_consignment_pdf(rows):
    """Generate a PDF BytesIO containing the provided consignment rows.

    `rows` is an iterable of objects with attributes used in the table.
    Returns a BytesIO ready to be sent (seeked to 0).
    """
    output = io.BytesIO()
    try:
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
        )
        styles = getSampleStyleSheet()

        table_data = [
            [
                "Consignment #",
                "Status",
                "Pickup Tag",
                "Drop Pin",
                "Pickup Date",
                "Drop Estimated",
            ]
        ]
        for row in rows:
            table_data.append(
                [
                    getattr(row, "consignment_number", "") or "",
                    getattr(row, "status", "") or "",
                    getattr(row, "pickup_tag", "") or "",
                    getattr(row, "drop_pincode", "") or "",
                    getattr(row, "pickup_date", "") or "",
                    getattr(row, "drop_date", "") or "",
                ]
            )

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9ECEF")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#6C757D")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        content = [
            Paragraph("Internal Consignment MIS", styles["Heading2"]),
            Spacer(1, 8),
            table,
        ]

        doc.build(content)
        output.seek(0)
        return output
    except Exception:
        logger.exception("PDF generation failed")
        output.seek(0)
        return output
