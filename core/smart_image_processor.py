"""
智能图片预处理器 - 提升OCR识别率
"""

import cv2
import numpy as np
import tempfile
import os
from typing import Tuple, List, Optional

class SmartImageProcessor:
    """智能图片预处理器"""
    
    def __init__(self):
        """初始化智能图片处理器"""
        self.max_size = 1280  # 最大图片尺寸
        self.min_size = 300   # 最小图片尺寸
    
    def auto_resize(self, image_path: str) -> Tuple[str, bool]:
        """自动调整图片尺寸"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path, False
            
            height, width = img.shape[:2]
            
            # 如果图片尺寸合适，直接返回
            if width <= self.max_size and height <= self.max_size and width >= self.min_size and height >= self.min_size:
                return image_path, False
            
            # 计算缩放比例
            if width > self.max_size or height > self.max_size:
                # 缩小大图片
                scale = min(self.max_size / width, self.max_size / height)
            else:
                # 放大小图片
                scale = max(self.min_size / width, self.min_size / height)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 缩放图片
            if scale != 1.0:
                resized_img = cv2.resize(img, (new_width, new_height), 
                                       interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
                
                # 保存到临时文件
                temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                os.close(temp_fd)
                cv2.imwrite(temp_path, resized_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                print(f"图片自动调整: {width}x{height} → {new_width}x{new_height} (缩放: {scale:.2f})")
                return temp_path, True
            
            return image_path, False
            
        except Exception as e:
            print(f"图片尺寸调整失败: {e}")
            return image_path, False
    
    def enhance_for_ocr(self, image_path: str, method: str = "standard") -> Tuple[str, bool]:
        """针对OCR优化图片质量"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path, False
            
            # 转换为灰度图
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            if method == "standard":
                enhanced = self._standard_enhancement(gray)
            elif method == "aggressive":
                enhanced = self._aggressive_enhancement(gray)
            elif method == "gentle":
                enhanced = self._gentle_enhancement(gray)
            else:
                enhanced = gray
            
            # 保存增强后的图片
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(temp_path, enhanced)
            
            print(f"图片增强完成: {method}方法")
            return temp_path, True
            
        except Exception as e:
            print(f"图片增强失败: {e}")
            return image_path, False
    
    def _standard_enhancement(self, gray_img):
        """标准增强方法"""
        # 自适应直方图均衡化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray_img)
        
        # 轻微去噪
        denoised = cv2.medianBlur(enhanced, 3)
        
        # 自适应二值化
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def _aggressive_enhancement(self, gray_img):
        """激进增强方法 - 用于困难图片"""
        # 强对比度增强
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray_img)
        
        # 强去噪
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # 锐化
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        # Otsu二值化
        _, binary = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _gentle_enhancement(self, gray_img):
        """温和增强方法 - 用于质量较好的图片"""
        # 轻微对比度增强
        enhanced = cv2.convertScaleAbs(gray_img, alpha=1.2, beta=10)
        
        # 轻微去噪
        denoised = cv2.medianBlur(enhanced, 3)
        
        return denoised
    
    def detect_text_regions(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """检测文本区域"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 使用MSER检测文本区域
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            # 转换为边界框
            bboxes = []
            for region in regions:
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
                # 过滤太小的区域
                if w > 20 and h > 10:
                    bboxes.append((x, y, w, h))
            
            return bboxes
            
        except Exception as e:
            print(f"文本区域检测失败: {e}")
            return []
    
    def crop_text_regions(self, image_path: str, padding: int = 20) -> List[str]:
        """裁剪文本区域"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            bboxes = self.detect_text_regions(image_path)
            if not bboxes:
                return []
            
            cropped_paths = []
            height, width = img.shape[:2]
            
            for i, (x, y, w, h) in enumerate(bboxes[:5]):  # 最多处理5个区域
                # 添加padding
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(width, x + w + padding)
                y2 = min(height, y + h + padding)
                
                # 裁剪区域
                cropped = img[y1:y2, x1:x2]
                
                # 保存裁剪的图片
                temp_fd, temp_path = tempfile.mkstemp(suffix=f'_crop_{i}.jpg')
                os.close(temp_fd)
                cv2.imwrite(temp_path, cropped)
                cropped_paths.append(temp_path)
            
            print(f"裁剪了 {len(cropped_paths)} 个文本区域")
            return cropped_paths
            
        except Exception as e:
            print(f"文本区域裁剪失败: {e}")
            return []
    
    def process_with_multiple_methods(self, image_path: str) -> List[Tuple[str, str]]:
        """使用多种方法处理图片"""
        processed_images = []
        temp_files = []
        
        try:
            # 1. 原始图片（调整尺寸）
            resized_path, is_temp = self.auto_resize(image_path)
            if is_temp:
                temp_files.append(resized_path)
            processed_images.append((resized_path, "原始"))
            
            # 2. 标准增强
            enhanced_path, is_temp = self.enhance_for_ocr(resized_path, "standard")
            if is_temp:
                temp_files.append(enhanced_path)
            processed_images.append((enhanced_path, "标准增强"))
            
            # 3. 激进增强（用于困难图片）
            aggressive_path, is_temp = self.enhance_for_ocr(resized_path, "aggressive")
            if is_temp:
                temp_files.append(aggressive_path)
            processed_images.append((aggressive_path, "激进增强"))
            
            return processed_images
            
        except Exception as e:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            print(f"多方法处理失败: {e}")
            return [(image_path, "原始")]
    
    def cleanup_temp_files(self, file_paths: List[str]):
        """清理临时文件"""
        for file_path in file_paths:
            try:
                if file_path != file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
