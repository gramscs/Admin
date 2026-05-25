from flask import jsonify


def json_error(message, code=500, **extra):
    """Return a standard JSON error response tuple (body, status).

    Body shape: {"success": False, "message": message, ...extra}
    """
    body = {"success": False, "message": message}
    if extra:
        body.update(extra)
    return jsonify(body), code


def json_success(payload=None, code=200):
    """Return a standard JSON success response.

    If `payload` is a dict, it will be merged with {"success": True}.
    If `payload` is None, returns {"success": True}.
    """
    if payload is None:
        body = {"success": True}
    elif isinstance(payload, dict):
        body = {"success": True, **payload}
    else:
        # non-dict payloads returned under the 'data' key
        body = {"success": True, "data": payload}

    return jsonify(body), code
