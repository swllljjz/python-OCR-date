"""
优化的PaddleOCR引擎 - 提升速度和准确率
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
from pathlib import Path
import time
import threading
import queue
import tempfile
import os

class OptimizedPaddleOCREngine:
    """优化的PaddleOCR引擎 - 专注速度和准确率"""
    
    def __init__(self):
        """初始化优化的PaddleOCR引擎"""
        print("正在初始化优化的PaddleOCR引擎...")
        
        try:
            # 尝试导入PaddleOCR
            from paddleocr import PaddleOCR
            
            # 创建PaddleOCR实例，优化参数以提升速度
            self.reader = PaddleOCR(
                use_angle_cls=True,       # 启用文字方向分类
                lang='ch',                # 中文识别
            )
            print("优化的PaddleOCR引擎初始化完成")
            
        except ImportError:
            print("PaddleOCR未安装，请运行: pip install paddlepaddle paddleocr")
            raise Exception("PaddleOCR未安装")
        except Exception as e:
            print(f"PaddleOCR初始化失败: {e}")
            raise
    
    def _smart_resize_image(self, image_path: str) -> Tuple[str, Tuple[int, int]]:
        """智能缩放图片以提升处理速度"""
        try:
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                return image_path, (0, 0)
            
            height, width = img.shape[:2]
            original_size = (width, height)
            
            # 如果图片尺寸合适，直接返回
            max_size = 1280
            if width <= max_size and height <= max_size:
                return image_path, original_size
            
            # 计算缩放比例
            scale = min(max_size / width, max_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 缩放图片
            resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # 保存到临时文件
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(temp_path, resized_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            print(f"图片缩放: {width}x{height} → {new_width}x{new_height} (缩放比例: {scale:.2f})")
            return temp_path, original_size
            
        except Exception as e:
            print(f"图片缩放失败: {e}")
            return image_path, (0, 0)
    
    def _enhance_image_for_ocr(self, image_path: str) -> str:
        """针对OCR优化图片质量"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path
            
            # 转换为灰度图
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 轻微去噪
            denoised = cv2.medianBlur(enhanced, 3)
            
            # 自适应二值化
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 保存增强后的图片
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(temp_path, binary)
            
            return temp_path
            
        except Exception as e:
            print(f"图片增强失败: {e}")
            return image_path
    
    def _calculate_dynamic_timeout(self, image_size: Tuple[int, int]) -> int:
        """根据图片大小动态计算超时时间"""
        width, height = image_size
        if width == 0 or height == 0:
            return 20
        
        # 基础超时时间
        base_timeout = 15
        
        # 根据像素数量调整
        pixels = width * height
        if pixels > 2000000:  # 大于200万像素
            return base_timeout + 15
        elif pixels > 1000000:  # 大于100万像素
            return base_timeout + 10
        elif pixels > 500000:   # 大于50万像素
            return base_timeout + 5
        else:
            return base_timeout
    
    def _ocr_worker(self, image_path: str, result_queue: queue.Queue):
        """OCR工作线程"""
        try:
            results = self.reader.predict(image_path)
            result_queue.put(('success', results))
        except Exception as e:
            result_queue.put(('error', str(e)))
    
    def ocr(self, image, timeout_seconds=None):
        """优化的OCR识别"""
        start_time = time.time()
        
        # 处理输入
        if isinstance(image, str):
            image_path = image
            original_size = (0, 0)
        else:
            # 图像数组，保存为临时文件
            temp_fd, image_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(image_path, image)
            original_size = (image.shape[1], image.shape[0])
        
        temp_files = []
        
        try:
            # 1. 智能缩放图片
            resized_path, detected_size = self._smart_resize_image(image_path)
            if resized_path != image_path:
                temp_files.append(resized_path)
            
            # 使用检测到的尺寸或原始尺寸
            final_size = detected_size if detected_size != (0, 0) else original_size
            
            # 2. 动态计算超时时间
            if timeout_seconds is None:
                timeout_seconds = self._calculate_dynamic_timeout(final_size)
            
            print(f"开始优化OCR识别 (图片尺寸: {final_size[0]}x{final_size[1]}, 超时: {timeout_seconds}秒)...")
            
            # 3. 第一次尝试：使用缩放后的图片
            result_queue = queue.Queue()
            worker_thread = threading.Thread(
                target=self._ocr_worker, 
                args=(resized_path, result_queue)
            )
            worker_thread.daemon = True
            worker_thread.start()
            
            try:
                status, results = result_queue.get(timeout=timeout_seconds)
                
                if status == 'success' and results and results[0]:
                    # 成功识别
                    formatted_results = self._format_results(results)
                    if formatted_results:
                        processing_time = time.time() - start_time
                        print(f"快速OCR识别成功: 找到 {len(formatted_results)} 个文本区域 (耗时: {processing_time:.2f}秒)")
                        return [formatted_results]
                
            except queue.Empty:
                print(f"第一次OCR识别超时，尝试图片增强...")
            
            # 4. 第二次尝试：图片增强
            enhanced_path = self._enhance_image_for_ocr(resized_path)
            if enhanced_path != resized_path:
                temp_files.append(enhanced_path)
            
            result_queue = queue.Queue()
            worker_thread = threading.Thread(
                target=self._ocr_worker, 
                args=(enhanced_path, result_queue)
            )
            worker_thread.daemon = True
            worker_thread.start()
            
            try:
                status, results = result_queue.get(timeout=timeout_seconds // 2)
                
                if status == 'success':
                    formatted_results = self._format_results(results)
                    processing_time = time.time() - start_time
                    
                    if formatted_results:
                        print(f"增强OCR识别成功: 找到 {len(formatted_results)} 个文本区域 (耗时: {processing_time:.2f}秒)")
                        return [formatted_results]
                    else:
                        print(f"增强OCR未识别到有效文本 (耗时: {processing_time:.2f}秒)")
                        return [[]]
                        
            except queue.Empty:
                processing_time = time.time() - start_time
                print(f"增强OCR识别也超时 (耗时: {processing_time:.2f}秒)")
                return [[]]
            
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            # 如果原始输入不是文件路径，清理临时文件
            if not isinstance(image, str):
                try:
                    os.unlink(image_path)
                except:
                    pass
    
    def _format_results(self, results):
        """格式化OCR结果"""
        formatted_results = []
        if results and len(results) > 0:
            ocr_result = results[0]
            
            if isinstance(ocr_result, dict) and 'rec_texts' in ocr_result:
                texts = ocr_result['rec_texts']
                scores = ocr_result.get('rec_scores', [])
                polys = ocr_result.get('rec_polys', [])
                
                for i in range(len(texts)):
                    try:
                        text = str(texts[i]).strip()
                        confidence = float(scores[i]) if i < len(scores) else 0.5
                        
                        # 降低置信度阈值以提高召回率
                        if confidence > 0.2 and len(text) > 0:
                            bbox = polys[i] if i < len(polys) else [[0,0],[0,0],[0,0],[0,0]]
                            if hasattr(bbox, 'tolist'):
                                bbox = bbox.tolist()
                            formatted_results.append([bbox, (text, confidence)])
                    except Exception as e:
                        continue
        
        return formatted_results
