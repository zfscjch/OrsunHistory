import cv2
import numpy as np
import os
import base64
from typing import Dict, Optional, Tuple
from flask import Blueprint, render_template, request, redirect
from PIL import Image, ImageEnhance
use_remote_face_server = False
try:
    from deepface import DeepFace
except ImportError:
    use_remote_face_server = True
from .get_user import get_user
from .api_response import api_response


class FaceRecognizer:
    def __init__(self, known_faces_dir="functions/db/known_faces"):
        self.known_faces_dir = os.path.abspath(known_faces_dir)

        # ========== 优化1: 使用更优秀的模型配置 ==========
        self.model_name = "ArcFace"  # 或 "ArcFace", "Facenet", "DeepFace"
        self.detector_backend = "retinaface"  # retinaface 是最准确的检测器
        self.distance_metric = "cosine"

        # ========== 优化2: 动态阈值调整 ==========
        self.base_threshold = 0.4  # 基础阈值
        self.min_threshold = 0.25  # 最小阈值（更严格）
        self.max_threshold = 0.55  # 最大阈值（更宽松）
        self.threshold = self.base_threshold

        # ========== 优化3: 多人脸支持 ==========
        self.max_faces = 5  # 最多检测的人脸数

        # ========== 优化4: 图像预处理配置 ==========
        self.preprocess_enabled = True
        self.face_size = (160, 160)  # 标准化人脸尺寸

        self.known_faces_cache = os.path.join(known_faces_dir, "known_faces_df.npy")
        self.known_faces = {}  # {name: embedding}
        self.known_faces_multiple = {}  # {name: [embedding1, embedding2, ...]}

        self._ensure_directory()
        res = self._load_faces_with_cache()
        if res == False:
            raise Exception("缓存加载失败！")
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
            data = np.load(self.known_faces_cache, allow_pickle=True).item()

            if isinstance(data, dict):
                self.known_faces = data
                print(f"✅ 从缓存加载 {len(self.known_faces)} 个人脸")
            else:
                print(f"⚠️ 缓存数据格式异常，将重新加载")
                self.known_faces = {}
                return False
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

        self.known_faces = {}
        image_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        loaded_count = 0

        for filename in os.listdir(self.known_faces_dir):
            if not filename.lower().endswith(image_exts):
                continue

            name = os.path.splitext(filename)[0]
            filepath = os.path.join(self.known_faces_dir, filename)

            try:
                # ========== 优化5: 多特征提取（从同一张图片中提取多个特征） ==========
                embeddings = self._extract_multiple_embeddings(filepath)

                if embeddings:
                    # 使用平均特征（更稳定）
                    avg_embedding = np.mean(embeddings, axis=0)
                    self.known_faces[name] = avg_embedding

                    # 保存多个特征用于投票
                    self.known_faces_multiple[name] = embeddings

                    loaded_count += 1
                    print(f"  ✅ 加载成功: {name} (提取了 {len(embeddings)} 个特征)")
                else:
                    print(f"  ⚠️ 未检测到人脸: {filename}")

            except Exception as e:
                print(f"  ❌ 提取失败 {filename}: {str(e)}")

        print(f"✅ 共加载 {loaded_count} 个人脸")

        if loaded_count > 0:
            self._save_cache()

    def _extract_multiple_embeddings(self, image_path, num_augmentations=3):
        """
        从一张图片提取多个特征（通过图像增强）
        """
        try:
            # 加载原始图片
            img = Image.open(image_path)
            rgb_img = np.array(img.convert('RGB'))

            embeddings = []

            # 1. 原始图片
            emb = self._extract_embedding(rgb_img)
            if emb is not None:
                embeddings.append(emb)

            # 2. 图像增强版本
            for i in range(num_augmentations):
                # 随机微调
                augmented = self._augment_image(img.copy())
                aug_rgb = np.array(augmented.convert('RGB'))
                emb = self._extract_embedding(aug_rgb)
                if emb is not None:
                    embeddings.append(emb)

            return embeddings if embeddings else None

        except Exception as e:
            print(f"提取多个特征失败: {e}")
            return None

    def _augment_image(self, img):
        """图像增强（用于提高鲁棒性）"""
        # 随机调整亮度和对比度
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.9 + 0.2 * np.random.random())

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(0.9 + 0.2 * np.random.random())

        # 随机旋转（小角度）
        if np.random.random() > 0.5:
            angle = np.random.uniform(-10, 10)
            img = img.rotate(angle, expand=False)

        return img

    def decode_base64_image(self, base64_string: str) -> np.ndarray:
        """将 Base64 字符串解码为 OpenCV 图像"""
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def _extract_embedding(self, image_array: np.ndarray) -> Optional[np.ndarray]:
        """从图像数组提取人脸特征"""
        try:
            # ========== 优化6: 图像预处理 ==========
            if self.preprocess_enabled:
                image_array = self._preprocess_image(image_array)

            embeddings = DeepFace.represent(
                img_path=image_array,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True,  # 启用面部对齐
                normalization="base"  # 归一化
            )
            if embeddings and len(embeddings) > 0:
                return np.array(embeddings[0]['embedding'])
            return None
        except Exception as e:
            print(f"提取特征失败: {e}")
            return None

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理：提高图像质量
        """
        try:
            # 如果输入是 RGB，转换为 BGR 进行处理
            if len(image.shape) == 3 and image.shape[2] == 3:
                # 转换为 BGR
                if image.dtype == np.uint8:
                    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                else:
                    bgr = image
            else:
                bgr = image

            # 1. 直方图均衡化（提高对比度）
            lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

            # 2. 锐化（增强边缘）
            kernel = np.array([[-1, -1, -1],
                               [-1, 9, -1],
                               [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # 3. 降噪（保持细节）
            denoised = cv2.fastNlMeansDenoisingColored(sharpened, None, 10, 10, 7, 21)

            # 转换回 RGB
            result = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)
            return result

        except Exception as e:
            print(f"预处理失败: {e}，使用原图")
            return image

    def _load_image(self, image_source) -> Optional[np.ndarray]:
        """统一的图片加载方法"""
        if isinstance(image_source, np.ndarray):
            if len(image_source.shape) == 3 and image_source.shape[2] == 3:
                return cv2.cvtColor(image_source, cv2.COLOR_BGR2RGB)
            return image_source

        if isinstance(image_source, Image.Image):
            return np.array(image_source.convert('RGB'))

        if isinstance(image_source, str):
            if image_source.startswith('data:image') or len(image_source) > 100:
                try:
                    img = self.decode_base64_image(image_source)
                    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                except:
                    pass

            if os.path.exists(image_source):
                img = Image.open(image_source)
                return np.array(img.convert('RGB'))

        return None

    def _calculate_distance(self, emb1, emb2):
        """计算两个特征向量的距离"""
        if self.distance_metric == "cosine":
            # 归一化后再计算余弦距离
            emb1_norm = emb1 / np.linalg.norm(emb1)
            emb2_norm = emb2 / np.linalg.norm(emb2)
            return 1 - np.dot(emb1_norm, emb2_norm)
        else:
            return np.linalg.norm(emb1 - emb2)

    # ========== 优化7: 多人脸识别 ==========
    def recognize_multiple_faces(self, image_source) -> Dict:
        """
        识别图片中的多张人脸
        """
        try:
            rgb_img = self._load_image(image_source)
            if rgb_img is None:
                return {"success": False, "message": "无法加载图片"}

            # 检测所有人脸
            face_objs = DeepFace.extract_faces(
                img_path=rgb_img,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )

            if not face_objs:
                return {"success": True, "faces": [], "count": 0, "message": "未检测到人脸"}

            results = []
            for face_obj in face_objs[:self.max_faces]:
                # 提取人脸区域
                face_img = (face_obj['face'] * 255).astype(np.uint8)

                # 提取特征
                embedding = self._extract_embedding(face_img)
                if embedding is None:
                    continue

                # 识别
                best_name, confidence = self._match_face(embedding)
                results.append({
                    "name": best_name,
                    "confidence": confidence,
                    "area": face_obj.get('area', {})
                })

            return {
                "success": True,
                "faces": results,
                "count": len(results),
                "message": f"检测到 {len(results)} 张人脸"
            }

        except Exception as e:
            print(f"❌ 多人脸识别失败: {str(e)}")
            return {"success": False, "message": f"识别失败: {str(e)}"}

    def _match_face(self, embedding) -> Tuple[str, float]:
        """
        匹配单张人脸，返回 (最佳匹配名称, 置信度)
        """
        if not self.known_faces:
            return "Unknown (No Database)", 0.0

        # 计算与所有人脸的距离
        distances = []
        for name, known_emb in self.known_faces.items():
            dist = self._calculate_distance(embedding, known_emb)
            distances.append((name, dist))

        # 按距离排序
        distances.sort(key=lambda x: x[1])

        best_name, best_distance = distances[0]

        # ========== 优化8: 动态阈值 ==========
        # 根据最佳距离调整阈值
        if best_distance < 0.15:
            # 非常匹配，降低阈值
            threshold = self.min_threshold
        elif best_distance < 0.3:
            threshold = self.base_threshold
        else:
            threshold = self.max_threshold

        # 判断是否匹配
        if best_distance < threshold:
            # ========== 优化9: 置信度计算 ==========
            # 使用 sigmoid 函数计算更平滑的置信度
            confidence = 1 / (1 + np.exp(10 * (best_distance - 0.15)))
            confidence = max(0, min(1, confidence))  # 限制在 [0, 1]
            return best_name, round(confidence, 3)
        else:
            # 检查是否有第二个候选，用于二次确认
            if len(distances) > 1:
                second_distance = distances[1][1]
                # 如果第一个和第二差距很大，说明匹配可靠
                if second_distance - best_distance > 0.15:
                    return best_name, round(0.5 * (1 - best_distance / threshold), 3)

            return "Unknown", 0.0

    def compare_with_database(self, image_source, return_all_matches: bool = False) -> Dict:
        """对比图片与数据库"""
        try:
            rgb_img = self._load_image(image_source)
            if rgb_img is None:
                return {"success": False, "message": "无法加载图片"}

            # ========== 优化10: 多角度匹配 ==========
            # 尝试多个角度/增强版本
            embeddings_list = []

            # 原始图片
            emb = self._extract_embedding(rgb_img)
            if emb is not None:
                embeddings_list.append(emb)

            # 翻转图片
            flipped = cv2.flip(rgb_img, 1)
            emb = self._extract_embedding(flipped)
            if emb is not None:
                embeddings_list.append(emb)

            if not embeddings_list:
                return {"success": False, "message": "未检测到人脸"}

            # 使用平均特征（更稳定）
            avg_embedding = np.mean(embeddings_list, axis=0)

            if not self.known_faces:
                return {"success": True, "message": "数据库中没有人脸数据", "matches": []}

            all_matches = []
            for name, known_emb in self.known_faces.items():
                dist = self._calculate_distance(avg_embedding, known_emb)
                is_match = dist < self.threshold
                confidence = 1 / (1 + np.exp(10 * (dist - 0.15))) if is_match else 0

                all_matches.append({
                    "name": name,
                    "distance": round(dist, 4),
                    "confidence": round(confidence, 3),
                    "is_match": is_match
                })

            all_matches.sort(key=lambda x: x["distance"])
            best_match = all_matches[0] if all_matches else None

            return {
                "success": True,
                "matches": all_matches if return_all_matches else [],
                "best_match": best_match,
                "total_in_database": len(self.known_faces),
                "message": f"找到 {len([m for m in all_matches if m['is_match']])} 个匹配"
            }

        except Exception as e:
            print(f"❌ 对比失败: {str(e)}")
            return {"success": False, "message": f"对比失败: {str(e)}", "matches": []}

    # ========== 原有方法保持不变 ==========
    def compare_two_images(self, image1_source, image2_source) -> Dict:
        """对比两张图片是否为同一个人"""
        try:
            img1 = self._load_image(image1_source)
            img2 = self._load_image(image2_source)

            if img1 is None or img2 is None:
                return {"success": False, "message": "无法加载图片"}

            emb1 = self._extract_embedding(img1)
            emb2 = self._extract_embedding(img2)

            if emb1 is None or emb2 is None:
                return {"success": False, "message": "未检测到人脸"}

            distance = self._calculate_distance(emb1, emb2)
            is_same = distance < self.threshold
            confidence = 1 / (1 + np.exp(10 * (distance - 0.15))) if is_same else 0

            return {
                "success": True,
                "is_same_person": is_same,
                "confidence": round(confidence, 3),
                "distance": round(distance, 4),
                "threshold": self.threshold,
                "message": "两张图片是同一人" if is_same else "两张图片不是同一人"
            }

        except Exception as e:
            print(f"❌ 对比失败: {str(e)}")
            return {"success": False, "message": f"对比失败: {str(e)}"}

    def find_matching_face(self, image_source, top_k: int = 1) -> Dict:
        """在数据库中查找最匹配的人脸"""
        result = self.compare_with_database(image_source, return_all_matches=True)

        if not result["success"]:
            return {
                "success": False,
                "message": result["message"],
                "matches": [],
                "best_match_name": None
            }

        matches = [m for m in result["matches"] if m["is_match"]]
        top_matches = matches[:top_k] if matches else []
        best_match_name = top_matches[0]["name"] if top_matches else None

        return {
            "success": True,
            "matches": top_matches,
            "best_match_name": best_match_name,
            "message": f"找到 {len(top_matches)} 个匹配" if top_matches else "未找到匹配的人脸"
        }

    def recognize_face(self, image_base64: str) -> Dict:
        """识别图片中的人脸（保持原有接口兼容）"""
        try:
            img = self.decode_base64_image(image_base64)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            face_objs = DeepFace.extract_faces(
                img_path=rgb_img,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )

            if not face_objs:
                return {
                    "success": True,
                    "faces": [],
                    "count": 0,
                    "message": "未检测到人脸"
                }

            embedding = self._extract_embedding(rgb_img)
            if embedding is None:
                return {
                    "success": True,
                    "faces": [],
                    "count": 0,
                    "message": "无法提取人脸特征"
                }

            if not self.known_faces:
                return {
                    "success": True,
                    "faces": [{"name": "Unknown (No Database)", "confidence": 0}],
                    "count": 1,
                    "message": "数据库为空"
                }

            best_name, confidence = self._match_face(embedding)

            return {
                "success": True,
                "faces": [{"name": best_name, "confidence": confidence}],
                "count": 1,
                "message": f"识别完成：{best_name}"
            }

        except Exception as e:
            print(f"❌ 识别错误: {str(e)}")
            return {"success": False, "error": str(e), "message": f"识别失败: {str(e)}"}

    def register_face(self, name: str, image_base64: str) -> Dict:
        """注册新用户"""
        try:
            img = self.decode_base64_image(image_base64)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 检测是否有人脸
            face_objs = DeepFace.extract_faces(
                img_path=rgb_img,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True
            )

            if not face_objs:
                return {"success": False, "message": "未检测到人脸，请重新拍摄"}

            # ========== 优化11: 注册时提取多个特征 ==========
            # 提取多个增强版本的特征，保存平均值
            embeddings = []

            # 原始
            emb = self._extract_embedding(rgb_img)
            if emb is not None:
                embeddings.append(emb)

            # 水平翻转
            flipped = cv2.flip(rgb_img, 1)
            emb = self._extract_embedding(flipped)
            if emb is not None:
                embeddings.append(emb)

            if not embeddings:
                return {"success": False, "message": "无法提取人脸特征"}

            # 使用平均特征
            avg_embedding = np.mean(embeddings, axis=0)

            # 删除同名旧图片
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

            # 更新内存
            self.known_faces[name] = avg_embedding
            self._save_cache()

            return {
                "success": True,
                "message": f"用户 {name} 注册成功（使用 {len(embeddings)} 个特征平均）",
            }

        except Exception as e:
            print(f"❌ 注册失败: {str(e)}")
            return {"success": False, "message": f"注册失败: {str(e)}"}


# ==================== Flask 路由 ====================

recognizer = None
if not use_remote_face_server:
    recognizer = FaceRecognizer()
else:
    print("将使用remote server进行人脸识别！")
face_bp = Blueprint('face', __name__)

@face_bp.route('/')
def get_index():
    return render_template("face.html")

@face_bp.route('/upload')
def get_upload():
    return render_template("upload_img.html")

@face_bp.route('/recognize', methods=['POST'])
def recognize():
    if use_remote_face_server:
        return redirect("https://www.cjchcoderchat.site:3/", 307)
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
    if use_remote_face_server:
        return redirect("https://www.cjchcoderchat.site:3/", 307)
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
