from typing import Literal
from flask import jsonify


def api_response(status: Literal["error", "success"], message="", data=None, http_code=200):
    res = {"status": status, "msg": message}
    if data:
        if type(data) == dict:
            res.update(data)
        else:
            res["data"] = data
    return jsonify(res), http_code