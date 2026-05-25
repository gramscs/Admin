"""Repository layer for Consignment DB operations.

Keep CRUD and query primitives here. Do NOT commit or rollback in this module;
transaction boundaries live in service layer.
"""
from typing import Optional, Tuple, List, Dict
from app.models import Consignment, db
from sqlalchemy import or_


def get_by_id(consignment_id: int) -> Optional[Consignment]:
    return db.session.get(Consignment, consignment_id)


def get_map_all() -> Dict[int, Consignment]:
    return {c.id: c for c in Consignment.query.all()}


def list_paginated(
    page: int = 1,
    per_page: int = 10,
    search: str = "",
    sort_by: str = "id",
    sort_order: str = "asc",
) -> Tuple[List[Consignment], int, int, bool, bool]:
    query = Consignment.query
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Consignment.consignment_number.ilike(pattern),
                Consignment.status.ilike(pattern),
                Consignment.pickup_tag.ilike(pattern),
                Consignment.drop_tag.ilike(pattern),
                Consignment.pickup_pincode.ilike(pattern),
                Consignment.drop_pincode.ilike(pattern),
                Consignment.pickup_address.ilike(pattern),
                Consignment.drop_address.ilike(pattern),
            )
        )

    total = query.count()
    sort_column = getattr(Consignment, sort_by, Consignment.id)
    if sort_order != "desc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return (
        paginated.items,
        total,
        paginated.pages,
        paginated.has_prev,
        paginated.has_next,
    )


def query_existing_numbers() -> set:
    rows = Consignment.query.with_entities(Consignment.consignment_number).all()
    return {r[0] for r in rows}


def add(instance: Consignment):
    db.session.add(instance)


def delete_by_id(consignment_id: int):
    inst = get_by_id(consignment_id)
    if inst:
        db.session.delete(inst)


def count() -> int:
    return Consignment.query.count()


def all_ordered() -> List[Consignment]:
    return Consignment.query.order_by(Consignment.id.asc()).all()


def flush():
    db.session.flush()
