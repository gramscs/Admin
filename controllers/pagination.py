"""Pagination helpers for controllers."""


def paginate_query(query, page=1, per_page=10, error_out=False):
    """Paginate a SQLAlchemy query and return (items, paginated_obj).

    The caller can inspect `paginated_obj` for `.pages`, `.has_prev`, `.has_next`, etc.
    """
    paginated = query.paginate(page=page, per_page=per_page, error_out=error_out)
    return paginated.items, paginated
