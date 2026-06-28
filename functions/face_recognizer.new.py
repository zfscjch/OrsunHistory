import cv2
import numpy as np
import os
import base64
from typing import Dict, Optional
from flask import Blueprint, render_template, request
from PIL import Image
from deepface import DeepFace

from .get_user import get_user
from .api_response import api_response


class FaceRecognizer:
    def __init__(self, known_faces_dir="functions/db/known_faces"):
        self.known_faces_dir = os.path.abspath(known_faces_dir)

        # DeepFace 配置
        self.model_name = "ArcFace"
        self.detector_backend = "retinaface"
        self.distance_metric = "cosine"
        self.threshold = 0.2
        self.known_faces_cache = os.path.join(known_faces_dir, "known_faces.npy")

        # 内存中存储已知人脸特征 {name: embedding}
        self.known_faces = {}

        # 确保目录存在并加载
        self._ensure_directory()
        self._load_faces_with_cache()

        # 如果缓存加载失败或为空，从图片目录加载
        if not self.known_faces:
            self.load_known_faces()

    def _ensure_directory(self):
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            print(f"✅ 创建目录: {self.known_faces_dir}")

    def _load_faces_with_cache(self):
        """从缓存文件加载人脸特征"""
        if not os.path.exists(self.known_faces_cache):
            print("ℹ️ 缓存文件不存在，将从图片目录加载")
            return

        try:
            # 加载缓存数据
            data = np.load(self.known_faces_cache, allow_pickle=True)

            # 检查加载的数据类型
            if isinstance(data, dict):
                # 如果是字典，直接使用
                self.known_faces = data
                print(f"✅ 从缓存加载 {len(self.known_faces)} 个人脸")
            elif isinstance(data, np.ndarray) and data.ndim == 0:
                # 如果是0维数组（标量），尝试提取其中的字典
                item = data.item()
                if isinstance(item, dict):
                    self.known_faces = item
                    print(f"✅ 从缓存加载 {len(self.known_faces)} 个人脸")
                else:
                    print(f"⚠️ 缓存数据格式异常: {type(item)}，将重新加载")
                    self.known_faces = {}
            else:
                # 其他情况，尝试转换为字典（兼容旧格式）
                try:
                    self.known_faces = dict(data)
                    print(f"✅ 从缓存加载 {len(self.known_faces)} 个人脸")
                except:
                    print(f"⚠️ 缓存数据无法转换为字典: {type(data)}，将重新加载")
                    self.known_faces = {}

        except Exception as e:
            print(f"⚠️ 缓存加载失败: {e}，将重新加载")
            self.known_faces = {}

    def _save_cache(self):
        """保存人脸特征到缓存文件"""
        try:
            np.save(self.known_faces_cache, self.known_faces, allow_pickle=True)
            print(f"💾 缓存已保存: {self.known_faces_cache}")
        except Exception as e:
            print(f"❌ 缓存保存失败: {e}")

    def load_known_faces(self):
        """从目录加载所有已知人脸特征到内存"""
        print(f"📂 加载已知人脸: {self.known_faces_dir}")

        if not os.path.exists(self.known_faces_dir):
            print(f"⚠️ 目录不存在: {self.known_faces_dir}")
            return

        # 清空现有数据（如果缓存加载失败）
        self.known_faces = {}

        image_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        loaded_count = 0

        for filename in os.listdir(self.known_faces_dir):
            if not filename.lower().endswith(image_exts):
                continue

            name = os.path.splitext(filename)[0]
            filepath = os.path.join(self.known_faces_dir, filename)

            try:
                # 使用 PIL 读取图片
                img = Image.open(filepath)
                rgb_img = np.array(img.convert('RGB'))

                # 提取特征（传入数组，而不是路径）
                embeddings = DeepFace.represent(
                    img_path=rgb_img,
                    model_name=self.model_name,
                    detector_backend=self.detector_backend,
                    enforce_detection=False
                )

                if embeddings and len(embeddings) > 0:
                    self.known_faces[name] = np.array(embeddings[0]['embedding'])
                    loaded_count += 1
                    print(f"  ✅ 加载成功: {name}")
                else:
                    print(f"  ⚠️ 未检测到人脸: {filename}")

            except Exception as e:
                print(f"  ❌ 提取失败 {filename}: {str(e)}")

        print(f"✅ 共加载 {loaded_count} 个人脸")

        # 保存缓存
        if loaded_count > 0:
            self._save_cache()

    def decode_base64_image(self, base64_string: str) -> np.ndarray:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def _extract_embedding(self, image_array: np.ndarray) -> Optional[np.ndarray]:
        """从图像数组提取人脸特征（第一个检测到的人脸）"""
        try:
            embeddings = DeepFace.represent(
                img_path=image_array,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            if embeddings and len(embeddings) > 0:
                return np.array(embeddings[0]['embedding'])
            return None
        except Exception as e:
            print(f"提取特征失败: {e}")
            return None

    def recognize_face(self, image_base64: str) -> Dict:
        """识别图片中的人脸（返回匹配的用户名）"""
        try:
            img = self.decode_base64_image(image_base64)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 检测人脸位置（用于返回坐标）
            face_objs = DeepFace.extract_faces(
                img_path=rgb_img,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            if not face_objs:
                return {
                    "success": True,
                    "faces": [],
                    "count": 0,
                    "message": "未检测到人脸"
                }

            # 提取待识别人脸的特征（只取第一张）
            face_embedding = self._extract_embedding(rgb_img)
            if face_embedding is None:
                return {
                    "success": True,
                    "faces": [],
                    "count": 0,
                    "message": "无法提取人脸特征"
                }

            # 如果没有已知人脸
            if not self.known_faces:
                return {
                    "success": True,
                    "faces": [{
                        "name": "Unknown (No Database)",
                        "confidence": 0
                    }],
                    "count": 1,
                    "message": "数据库为空"
                }

            # 计算与所有已知人脸的距离
            best_name = None
            best_distance = float('inf')
            for name, known_emb in self.known_faces.items():
                if self.distance_metric == "cosine":
                    dist = 1 - np.dot(face_embedding, known_emb) / (
                            np.linalg.norm(face_embedding) * np.linalg.norm(known_emb)
                    )
                else:
                    dist = np.linalg.norm(face_embedding - known_emb)

                if dist < best_distance:
                    best_distance = dist
                    best_name = name

            # 判断是否匹配
            if best_distance < self.threshold and best_name:
                confidence = max(0, 1 - (best_distance / self.threshold))
                name = best_name
            else:
                name = "Unknown"
                confidence = 0

            return {
                "success": True,
                "faces": [{
                    "name": name,
                    "confidence": round(confidence, 3)
                }],
                "count": 1,
                "message": f"识别完成：{name}"
            }

        except Exception as e:
            print(f"❌ 识别错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"识别失败: {str(e)}"
            }

    def register_face(self, name: str, image_base64: str) -> Dict:
        """注册新用户：保存图片并更新内存特征"""
        try:
            img = self.decode_base64_image(image_base64)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 检测是否有人脸（使用数组）
            face_objs = DeepFace.extract_faces(
                img_path=rgb_img,
                detector_backend=self.detector_backend,
                enforce_detection=True  # 必须检测到
            )

            if not face_objs:
                return {"success": False, "message": "未检测到人脸，请重新拍摄"}

            # 提取特征
            embedding = self._extract_embedding(rgb_img)
            if embedding is None:
                return {"success": False, "message": "无法提取人脸特征"}

            # 删除同名旧图片（支持多种扩展名）
            for ext in ['.png', '.jpg', '.jpeg']:
                old_path = os.path.join(self.known_faces_dir, f"{name}{ext}")
                if os.path.exists(old_path):
                    os.remove(old_path)
                    print(f"🗑️ 删除旧照片: {old_path}")

            # 保存新图片
            save_path = os.path.join(self.known_faces_dir, f"{name}.png")
            pil_img = Image.fromarray(rgb_img)
            pil_img.save(save_path)
            print(f"💾 图片已保存: {save_path}")

            # 更新内存特征
            self.known_faces[name] = embedding

            # 保存缓存（注意：保存的是字典，不是目录路径）
            self._save_cache()

            return {
                "success": True,
                "message": f"用户 {name} 注册成功",
            }

        except Exception as e:
            print(f"❌ 注册失败: {str(e)}")
            return {"success": False, "message": f"注册失败: {str(e)}"}


# ==================== Flask 路由 ====================

recognizer = FaceRecognizer()
face_bp = Blueprint('face', __name__)

@face_bp.route('/')
def get_index():
    return render_template("face.html")

@face_bp.route('/upload')
def get_upload():
    return render_template("upload_img.html")

@face_bp.route('/recognize', methods=['POST'])
def recognize():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return api_response("error", "请提供图片数据", http_code=400)

        result = recognizer.recognize_face(data['image'])
        if not result['success']:
            return api_response("error", result.get('message', '识别失败'), http_code=400)

        # 检查识别结果
        for face in result.get("faces", []):
            name = face.get("name")
            if name and name not in ["Unknown", "Unknown (No Database)"]:
                status, msg = get_user(name)
                if status == "success":
                    return api_response("success", "", msg)

        return api_response("error", result["message"], http_code=400)
    except Exception as e:
        print(f"❌ 识别接口错误: {str(e)}")
        return api_response("error", f"服务器错误: {str(e)}", http_code=500)

@face_bp.route("/register", methods=["POST"])
def register_user():
    try:
        data = request.json
        if not data or 'name' not in data or 'image' not in data:
            return api_response("error", "请提供用户名和图片数据", http_code=400)

        name = data['name'].strip()
        if not name:
            return api_response("error", "用户名不能为空", http_code=400)

        result = recognizer.register_face(name, data['image'])
        if result['success']:
            status, msg = get_user(name)
            return api_response(status, "", msg)
        else:
            return api_response("error", result['message'], http_code=400)
    except Exception as e:
        print(f"❌ 注册接口错误: {str(e)}")
        return api_response("error", f"服务器错误: {str(e)}", http_code=500)