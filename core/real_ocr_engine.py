import easyocr
import numpy as np
import cv2
from typing import List, Optional
from pathlib import Path
import time
import threading
import queue

class TimeoutError(Exception):
    """超时异常"""
    pass

class RealOCREngine:
    """优化的真正OCR引擎 - 基于EasyOCR"""

    def __init__(self):
        """初始化EasyOCR"""
        print("正在初始化优化的EasyOCR引擎...")
        print("首次运行会下载模型文件，请稍候...")

        # 创建EasyOCR读取器，支持中文和英文
        self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        print("优化的OCR引擎初始化完成")
    
    def preprocess_image_method1(self, image):
        """预处理方法1: 标准预处理"""
        try:
            # 如果是文件路径，先读取图片
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    return None
            else:
                img = image.copy()

            # 转换为灰度图
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            # 调整图片大小
            height, width = gray.shape
            if height < 200 or width < 200:
                scale = max(200/height, 200/width, 2.0)
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

            # 增强对比度
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)

            # 去噪
            denoised = cv2.medianBlur(enhanced, 3)

            # OTSU二值化
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            return binary

        except Exception as e:
            print(f"预处理方法1失败: {e}")
            return None

    def preprocess_image_method2(self, image):
        """预处理方法2: 自适应阈值"""
        try:
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    return None
            else:
                img = image.copy()

            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            # 调整大小
            height, width = gray.shape
            if height < 300 or width < 300:
                scale = max(300/height, 300/width, 1.5)
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

            # 高斯模糊去噪
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # 自适应阈值
            binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)

            return binary

        except Exception as e:
            print(f"预处理方法2失败: {e}")
            return None

    def preprocess_image_method3(self, image):
        """预处理方法3: 形态学处理"""
        try:
            if isinstance(image, str):
                img = cv2.imread(image)
                if img is None:
                    return None
            else:
                img = image.copy()

            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img

            # 调整大小
            height, width = gray.shape
            if height < 250 or width < 250:
                scale = max(250/height, 250/width, 2.0)
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

            # 直方图均衡化
            equalized = cv2.equalizeHist(gray)

            # 二值化
            _, binary = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            return binary

        except Exception as e:
            print(f"预处理方法3失败: {e}")
            return None

    def _ocr_worker(self, processed_image, result_queue):
        """OCR工作线程"""
        try:
            results = self.reader.readtext(processed_image)
            result_queue.put(('success', results))
        except Exception as e:
            result_queue.put(('error', str(e)))

    def ocr(self, image, timeout_seconds=15):
        """简化的OCR识别，使用最佳预处理方法"""
        start_time = time.time()

        print(f"开始OCR识别 (超时: {timeout_seconds}秒)...")

        try:
            # 使用标准预处理方法（效果最好）
            processed_image = self.preprocess_image_method1(image)
            if processed_image is None:
                print("图片预处理失败")
                return [[]]

            # OCR识别
            result_queue = queue.Queue()
            worker_thread = threading.Thread(
                target=self._ocr_worker,
                args=(processed_image, result_queue)
            )
            worker_thread.daemon = True
            worker_thread.start()

            try:
                # 等待结果
                status, results = result_queue.get(timeout=timeout_seconds)

                if status == 'error':
                    print(f"OCR识别失败: {results}")
                    return [[]]

            except queue.Empty:
                print(f"OCR识别超时 ({timeout_seconds}秒)")
                return [[]]

            # 转换结果格式
            formatted_results = []
            for bbox, text, confidence in results:
                # 宽松的过滤条件
                if confidence > 0.2 and len(text.strip()) > 0:
                    cleaned_text = text.strip()
                    formatted_results.append([bbox, (cleaned_text, confidence)])

            processing_time = time.time() - start_time

            if formatted_results:
                print(f"OCR识别成功: 找到 {len(formatted_results)} 个文本区域 (耗时: {processing_time:.2f}秒)")

                # 显示识别结果
                for i, (bbox, (text, conf)) in enumerate(formatted_results[:5]):  # 只显示前5个
                    print(f"  {i+1}. '{text}' (置信度: {conf:.2f})")

                if len(formatted_results) > 5:
                    print(f"  ... 还有 {len(formatted_results) - 5} 个文本")

                return [formatted_results]
            else:
                print(f"OCR未识别到任何文本 (耗时: {processing_time:.2f}秒)")
                return [[]]

        except Exception as e:
            processing_time = time.time() - start_time
            print(f"OCR识别异常: {e} (耗时: {processing_time:.2f}秒)")
            return [[]]
