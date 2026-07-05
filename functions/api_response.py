from typing import Literal
from flask import jsonify, g


def api_response(status: Literal["error", "success"], message="", data=None, http_code=200):
    res = {"status": status, "msg": message}
    if data:
        if type(data) == dict:
            res.update(data)
        else:
            res["data"] = data
    return jsonify(res), http_code


def request_not_json_res():
    return api_response("error", "请求必须为 JSON", http_code=400)


def request_miss_arg_res():
    return api_response("error", "缺少必要参数", http_code=400)


def server_error_res(action: str, e: Exception):
    log_mgr = g.log_mgr
    log_mgr.error("sys", f"在{action}时发生错误：{e}", "127.0.0.1")
    return api_response("error", f"发生错误：{e}", http_code=500)
