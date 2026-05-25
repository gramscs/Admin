"""Model serialization helpers used by controllers and routes."""


def serialize_consignment(c):
    """Return a lightweight dict representation of a Consignment row."""
    return {
        "id": c.id,
        "consignment_number": c.consignment_number,
        "status": c.status,
        "pickup_pincode": c.pickup_pincode,
        "pickup_address": getattr(c, "pickup_address", None),
        "pickup_tag": getattr(c, "pickup_tag", None),
        "pickup_date": getattr(c, "pickup_date", None),
        "drop_pincode": c.drop_pincode,
        "drop_address": getattr(c, "drop_address", None),
        "drop_tag": getattr(c, "drop_tag", None),
        "drop_date": getattr(c, "drop_date", None),
        "eta": getattr(c, "eta", None),
        "pod_image": getattr(c, "pod_image", None),
    }
