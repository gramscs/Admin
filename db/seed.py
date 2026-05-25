"""Moved from __init__.py."""

import logging
import os

from app.models import Consignment
from app.db.session import transaction


logger = logging.getLogger(__name__)


def seed_development_data(db, app):
    if os.getenv("FLASK_ENV", "").strip().lower() != "development":
        return

    try:
        # If the DB already has 100 or more consignments, do nothing.
        existing_count = Consignment.query.count()
        if existing_count >= 100:
            return

        # Build deterministic sample consignments and avoid duplicates.
        sample_consignment_data = []
        statuses = ["Pickup Scheduled", "In Transit", "Out for Delivery", "Delivered"]
        existing_numbers = {
            row[0]
            for row in Consignment.query.with_entities(
                Consignment.consignment_number
            ).all()
        }

        for i in range(1, 101):
            cn = f"DEV{str(i).zfill(4)}"
            if cn in existing_numbers:
                continue

            status = statuses[i % len(statuses)]
            pickup_pincode = str(110000 + (i % 900000))[:6]
            drop_pincode = str(400000 + (i % 500000))[:6]
            pickup_address = f"{i} Dev Pickup St, Dev City {i % 10}"
            drop_address = f"{i} Dev Drop Ave, Dest City {i % 10}"
            pickup_date = f"2026-05-{(i % 28) + 1:02d}"
            drop_date = f"2026-06-{(i % 28) + 1:02d}"
            eta = f"2026-06-{(i % 28) + 1:02d} 12:00"

            sample_consignment_data.append(
                Consignment(
                    consignment_number=cn,
                    status=status,
                    pickup_address=pickup_address,
                    pickup_pincode=pickup_pincode,
                    pickup_date=pickup_date,
                    drop_address=drop_address,
                    drop_pincode=drop_pincode,
                    drop_date=drop_date,
                    eta=eta,
                    pickup_tag=f"PICK{i % 5}",
                    drop_tag=f"DROP{i % 7}",
                )
            )

        # Only add as many rows as necessary to reach 100 total.
        to_add = []
        remaining = max(0, 100 - existing_count)
        for item in sample_consignment_data:
            if remaining <= 0:
                break
            to_add.append(item)
            remaining -= 1

        if to_add:
            try:
                with transaction(db):
                    db.session.add_all(to_add)
            except Exception as e:
                logger.exception("Failed to seed development consignments: %s", e)

        logger.info(
            "Seeded development consignments; total now %d (added %d)",
            Consignment.query.count(),
            len(to_add),
        )
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            logger.exception("Failed to rollback DB session during seeding")
        logger.exception("Failed to seed development consignments: %s", e)
