"""
PaddleOCR引擎 - 专业的中文OCR识别引擎
"""

import cv2
import numpy as np
from typing import List, Optional
from pathlib import Path
import time
import threading
import queue

class PaddleOCREngine:
    """PaddleOCR引擎 - 专门针对中文优化"""
    
    def __init__(self):
        """初始化PaddleOCR引擎"""
        print("正在初始化PaddleOCR引擎...")
        print("首次运行会下载模型文件，请稍候...")
        
        try:
            # 尝试导入PaddleOCR
            from paddleocr import PaddleOCR
            
            # 创建PaddleOCR实例，使用默认参数
            self.reader = PaddleOCR(use_angle_cls=True, lang='ch')
            print("PaddleOCR引擎初始化完成")
            
        except ImportError:
            print("PaddleOCR未安装，请运行: pip install paddlepaddle paddleocr")
            raise Exception("PaddleOCR未安装")
        except Exception as e:
            print(f"PaddleOCR初始化失败: {e}")
            raise
    
    def preprocess_image_for_date(self, image):
        """专门针对日期识别的图片预处理"""
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
            
            # 调整图片大小 - 确保足够大以便识别
            height, width = gray.shape
            if height < 300 or width < 300:
                scale = max(300/height, 300/width, 2.0)
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # 对比度增强 - 使用CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 去噪处理
            denoised = cv2.medianBlur(enhanced, 3)
            
            # 锐化处理 - 增强文字边缘
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # 自适应二值化 - 对不同光照条件更鲁棒
            binary = cv2.adaptiveThreshold(
                sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 形态学操作 - 连接断开的文字
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return binary
            
        except Exception as e:
            print(f"图片预处理失败: {e}")
            return image
    
    def _ocr_worker(self, image_path, result_queue):
        """OCR工作线程"""
        try:
            # 使用新的predict方法，直接传递图片路径
            results = self.reader.predict(image_path)
            result_queue.put(('success', results))
        except Exception as e:
            result_queue.put(('error', str(e)))

    def ocr(self, image, timeout_seconds=15):
        """PaddleOCR识别，专门优化日期识别"""
        start_time = time.time()
        
        print(f"开始PaddleOCR识别 (超时: {timeout_seconds}秒)...")
        
        try:
            # 处理不同类型的输入
            if isinstance(image, str):
                # 文件路径，直接使用
                image_path = image
            else:
                # 图像数组，需要保存为临时文件
                import tempfile
                import cv2

                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    temp_path = tmp_file.name
                    cv2.imwrite(temp_path, image)
                    image_path = temp_path

            # OCR识别 - 使用处理后的图片路径
            result_queue = queue.Queue()
            worker_thread = threading.Thread(
                target=self._ocr_worker,
                args=(image_path, result_queue)
            )
            worker_thread.daemon = True
            worker_thread.start()
            
            try:
                # 等待结果
                status, results = result_queue.get(timeout=timeout_seconds)
                
                if status == 'error':
                    print(f"PaddleOCR识别失败: {results}")
                    return [[]]
                    
            except queue.Empty:
                print(f"PaddleOCR识别超时 ({timeout_seconds}秒)")
                return [[]]
            
            # 转换为统一格式
            formatted_results = []
            if results and len(results) > 0:
                ocr_result = results[0]

                # 检查是否是新版本的OCRResult字典对象
                if isinstance(ocr_result, dict) and 'rec_texts' in ocr_result and 'rec_scores' in ocr_result:
                    # 新版本PaddleOCR的OCRResult字典
                    texts = ocr_result['rec_texts']
                    scores = ocr_result['rec_scores']
                    polys = ocr_result.get('rec_polys', [])

                    for i in range(len(texts)):
                        try:
                            text = str(texts[i]).strip()
                            confidence = float(scores[i])

                            # 获取边界框，如果没有则使用默认值
                            if i < len(polys):
                                poly = polys[i]
                                # 将numpy数组转换为列表格式
                                if hasattr(poly, 'tolist'):
                                    bbox = poly.tolist()
                                else:
                                    bbox = poly
                            else:
                                bbox = [[0,0],[0,0],[0,0],[0,0]]

                            # 过滤条件：置信度 > 0.3，文本长度 > 0
                            if confidence > 0.3 and len(text) > 0:
                                formatted_results.append([bbox, (text, confidence)])
                        except Exception as e:
                            print(f"解析OCRResult第{i}项失败: {e}")
                            continue

                elif isinstance(ocr_result, (list, tuple)):
                    # 旧版本格式
                    for line in ocr_result:
                        try:
                            if len(line) >= 2:
                                bbox = line[0]  # 边界框
                                text_info = line[1]  # 文本和置信度

                                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                    text = str(text_info[0]).strip()
                                    confidence = float(text_info[1])

                                    # 过滤条件：置信度 > 0.3，文本长度 > 0
                                    if confidence > 0.3 and len(text) > 0:
                                        formatted_results.append([bbox, (text, confidence)])
                        except Exception as e:
                            print(f"解析单行结果失败: {e}")
                            continue
            
            processing_time = time.time() - start_time

            # 清理临时文件
            if not isinstance(image, str) and 'temp_path' in locals():
                try:
                    import os
                    os.unlink(temp_path)
                except:
                    pass

            if formatted_results:
                print(f"PaddleOCR识别成功: 找到 {len(formatted_results)} 个文本区域 (耗时: {processing_time:.2f}秒)")

                # 显示识别结果
                for i, (bbox, (text, conf)) in enumerate(formatted_results[:5]):
                    print(f"  {i+1}. '{text}' (置信度: {conf:.2f})")

                if len(formatted_results) > 5:
                    print(f"  ... 还有 {len(formatted_results) - 5} 个文本")

                return [formatted_results]
            else:
                print(f"PaddleOCR未识别到任何文本 (耗时: {processing_time:.2f}秒)")
                return [[]]
                
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"PaddleOCR识别异常: {e} (耗时: {processing_time:.2f}秒)")
            return [[]]
