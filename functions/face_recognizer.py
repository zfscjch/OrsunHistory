import face_recognition
import cv2
import numpy as np
import os
import base64
from typing import Dict
from flask import Blueprint, render_template, request
from PIL import Image
from .get_user import get_user
from .api_response import api_response


class FaceRecognizer:
    def __init__(self, known_faces_dir="functions/db/known_faces"):
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_faces_dir = known_faces_dir
        self.cache_enc = os.path.join(known_faces_dir, "encodings.npy")
        self.cache_names = os.path.join(known_faces_dir, "names.npy")
        self.load_cache()
        self.load_known_faces()

    def load_cache(self):
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            print(f"创建了 {self.known_faces_dir} 文件夹，请放入已知人脸照片")
            return

        print(f"加载已知人脸：{self.known_faces_dir}")
        if os.path.exists(self.cache_enc) and os.path.exists(self.cache_names):
            try:
                self.known_face_encodings = list(np.load(self.cache_enc, allow_pickle=True))
                self.known_face_names = list(np.load(self.cache_names, allow_pickle=True))
                print(f"从NumPy缓存加载 {len(self.known_face_names)} 人")
                return
            except:
                pass

    def load_known_faces(self):
        """从文件夹加载已知人脸"""
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            print(f"创建了 {self.known_faces_dir} 文件夹，请放入已知人脸照片")
            return

        if not self.known_face_encodings or not self.known_face_names:
            for filename in os.listdir(self.known_faces_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    name = os.path.splitext(filename)[0]
                    image_path = os.path.join(self.known_faces_dir, filename)

                    try:
                        # 加载图片
                        image = face_recognition.load_image_file(image_path)
                        # 提取人脸特征
                        encodings = face_recognition.face_encodings(image)

                        if len(encodings) > 0:
                            self.known_face_encodings.append(encodings[0])
                            self.known_face_names.append(name)
                            print(f"✓ 已加载：{name}")
                        else:
                            print(f"✗ 未检测到人脸：{filename}")
                    except Exception as e:
                        print(f"✗ 加载失败 {filename}: {e}")

        np.save(self.cache_enc, np.array(self.known_face_encodings))
        np.save(self.cache_names, np.array(self.known_face_names))

        print(f"加载完成！共 {len(self.known_face_names)} 人")

    def decode_base64_image(self, base64_string: str) -> np.ndarray:
        """将Base64编码的图像解码为OpenCV格式"""
        # 移除base64头部信息（如"data:image/jpeg;base64,"）
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]

        # 解码
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def recognize_face(self, image_base64: str) -> Dict:
        """
        识别单张图片中的所有人脸
        """
        try:
            # 解码图像
            img = self.decode_base64_image(image_base64)

            # 转换为RGB格式（face_recognition需要）
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 检测人脸位置
            face_locations = face_recognition.face_locations(rgb_img)

            if not face_locations:
                return {
                    "success": True,
                    "faces": [],
                    "count": 0,
                    "message": "未检测到人脸"
                }

            # 提取人脸特征
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

            results = []
            for face_encoding, face_location in zip(face_encodings, face_locations):
                if not self.known_face_encodings:
                    # 如果没有已知人脸数据库
                    results.append({
                        "name": "Unknown (No Database)",
                        "confidence": 0,
                        "location": face_location
                    })
                    continue

                # 计算与所有人脸的距离
                distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(distances)
                min_distance = distances[best_match_index]

                # 阈值判断（0.6是常用的经验值）
                threshold = 0.6
                if min_distance < threshold:
                    name = self.known_face_names[best_match_index]
                    confidence = 1 - (min_distance / threshold)  # 转换为置信度百分比
                    results.append({
                        "name": name,
                        "confidence": round(confidence, 3),
                        "location": face_location  # (top, right, bottom, left)
                    })
                else:
                    results.append({
                        "name": "Unknown",
                        "confidence": 0,
                        "location": face_location
                    })

            return {
                "success": True,
                "faces": results,
                "count": len(results),
                "message": f"检测到 {len(results)} 张人脸"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"识别失败: {str(e)}"
            }


    def register_face(self, name: str, image_base64: str) -> Dict:
        """注册新用户（将人脸添加到数据库）"""
        try:
            # 解码图像
            img = self.decode_base64_image(image_base64)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 检测人脸
            face_locations = face_recognition.face_locations(rgb_img)
            if not face_locations:
                return {
                    "success": False,
                    "message": "未检测到人脸，请重新拍摄"
                }

            # 提取特征
            face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
            if not face_encodings:
                return {
                    "success": False,
                    "message": "无法提取人脸特征"
                }

            # ========== 改进1：统一文件命名和清理 ==========
            # 定义支持的图片扩展名列表
            image_extensions = ['.png', '.jpg', '.jpeg']

            # 删除所有可能存在的旧图片
            for ext in image_extensions:
                old_path = os.path.join(self.known_faces_dir, f"{name}{ext}")
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                        print(f"删除旧照片：{old_path}")
                    except Exception as e:
                        print(f"删除旧照片失败 {old_path}: {e}")

            # ========== 改进2：保存图片并检查返回值 ==========
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 2. 从 numpy 数组创建 Pillow Image 对象
            pil_img = Image.fromarray(img_rgb)

            # 3. 确保目录存在，然后保存
            save_path = os.path.join(self.known_faces_dir, f"{name}.png")
            pil_img.save(save_path)

            print(f"图片已保存：{save_path}")

            # ========== 改进4：更新内存和缓存 ==========
            if name in self.known_face_names:
                print(f"更新已有用户：{name}")
                self.known_face_encodings[self.known_face_names.index(name)] = face_encodings[0]
            else:
                self.known_face_encodings.append(face_encodings[0])
                self.known_face_names.append(name)

            # 保存缓存
            np.save(self.cache_enc, np.array(self.known_face_encodings))
            np.save(self.cache_names, np.array(self.known_face_names))

            return {
                "success": True,
                "message": f"用户 {name} 注册成功",
                "face_location": face_locations[0]
            }

        except Exception as e:
            print(f"注册失败详细错误：{str(e)}")
            return {
                "success": False,
                "message": f"注册失败: {str(e)}"
            }

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
    """人脸识别接口"""
    try:
        # 获取请求数据
        data = request.json
        if not data or 'image' not in data:
            return api_response("error", "请提供图片数据", http_code=400)

        image_base64 = data['image']

        # 执行识别
        result = recognizer.recognize_face(image_base64)

        print(f"识别完成 - 检测到 {result.get('count', 0)} 张人脸")
        for f in result["faces"]:
            if f["name"] != "Unknown":
                status, msg = get_user(f["name"])
                return api_response(status, "", msg)

        return api_response("error", "没有此用户", http_code=400)
    except Exception as e:
        print(f"识别接口错误: {str(e)}")
        return api_response("error",f"服务器错误: {str(e)}", http_code=500)


@face_bp.route("/register", methods=["POST"])
def register_user():
    """用户注册接口"""
    try:
        data = request.json
        if not data or 'name' not in data or 'image' not in data:
            return api_response("error", "请提供用户名和图片数据", http_code=400)

        name = data['name']
        image_base64 = data['image']

        # 执行注册
        result = recognizer.register_face(name, image_base64)

        if result['success']:
            print(f"新用户注册成功: {name}")
        else:
            print(f"用户注册失败: {name} - {result['message']}")

        status, msg = get_user(name)
        return api_response(status, "", msg)
    except Exception as e:
        print(f"注册接口错误: {str(e)}")
        return api_response("error", f"服务器错误: {str(e)}", http_code=500)