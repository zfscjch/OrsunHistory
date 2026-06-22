import json

def load_titles(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as rf:
            data = json.load(rf)
        return data, 200
    except FileNotFoundError:
        return "题目文件不存在", 500
    except json.JSONDecodeError:
        return "题目文件格式错误", 500
    except Exception as e:
        return f"{type(e).__name__}:{e}", 500

def save_data(d, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as rf:
            old = json.load(rf)
        old.append({"user": d["name"], "num": d["msg"]["num"], "isRight": d["msg"]["isRight"]})
        with open(file_path, "w", encoding="utf-8") as wf:
            json.dump(old, wf, ensure_ascii=False)
        return "success", 200
    except FileNotFoundError:
        return "文件不存在", 500
    except json.JSONDecodeError:
        return "返回值格式错误", 500
    except Exception as e:
        return f"{type(e).__name__}:{e}", 500