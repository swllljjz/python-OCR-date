"""
智能ROI检测器 - 提升OCR处理速度
只对文本区域进行OCR识别，大幅减少处理时间
"""

import cv2
import numpy as np
import tempfile
import os
from typing import List, Tuple, Optional

class SmartROIDetector:
    """智能ROI(感兴趣区域)检测器"""
    
    def __init__(self):
        """初始化ROI检测器"""
        self.min_text_area = 100      # 最小文本区域面积
        self.max_text_area = 50000    # 最大文本区域面积
        self.min_aspect_ratio = 0.1   # 最小宽高比
        self.max_aspect_ratio = 10.0  # 最大宽高比
        
    def detect_text_regions(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """检测图片中的文本区域
        
        Returns:
            List of (x, y, width, height) tuples representing text regions
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 使用多种方法检测文本区域
            regions = []
            
            # 方法1: MSER检测
            mser_regions = self._detect_with_mser(gray)
            regions.extend(mser_regions)
            
            # 方法2: 边缘检测 + 轮廓
            edge_regions = self._detect_with_edges(gray)
            regions.extend(edge_regions)
            
            # 方法3: 形态学操作
            morph_regions = self._detect_with_morphology(gray)
            regions.extend(morph_regions)
            
            # 合并和过滤区域
            filtered_regions = self._filter_and_merge_regions(regions, img.shape[:2])
            
            print(f"检测到 {len(filtered_regions)} 个文本区域")
            return filtered_regions
            
        except Exception as e:
            print(f"文本区域检测失败: {e}")
            return []
    
    def _detect_with_mser(self, gray_img) -> List[Tuple[int, int, int, int]]:
        """使用MSER算法检测文本区域"""
        try:
            # 创建MSER检测器
            mser = cv2.MSER_create(
                _min_area=self.min_text_area,
                _max_area=self.max_text_area,
                _max_variation=0.25,
                _min_diversity=0.2
            )
            
            # 检测区域
            regions, _ = mser.detectRegions(gray_img)
            
            # 转换为边界框
            bboxes = []
            for region in regions:
                x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
                if self._is_valid_text_region(w, h):
                    bboxes.append((x, y, w, h))
            
            return bboxes
            
        except Exception as e:
            print(f"MSER检测失败: {e}")
            return []
    
    def _detect_with_edges(self, gray_img) -> List[Tuple[int, int, int, int]]:
        """使用边缘检测方法"""
        try:
            # 边缘检测
            edges = cv2.Canny(gray_img, 50, 150)
            
            # 形态学操作连接文本
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 转换为边界框
            bboxes = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if self._is_valid_text_region(w, h):
                    bboxes.append((x, y, w, h))
            
            return bboxes
            
        except Exception as e:
            print(f"边缘检测失败: {e}")
            return []
    
    def _detect_with_morphology(self, gray_img) -> List[Tuple[int, int, int, int]]:
        """使用形态学操作检测文本"""
        try:
            # 二值化
            _, binary = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 水平和垂直形态学操作
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
            
            # 检测水平和垂直线
            horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
            vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
            
            # 合并
            combined = cv2.addWeighted(horizontal, 0.5, vertical, 0.5, 0)
            
            # 查找轮廓
            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 转换为边界框
            bboxes = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if self._is_valid_text_region(w, h):
                    bboxes.append((x, y, w, h))
            
            return bboxes
            
        except Exception as e:
            print(f"形态学检测失败: {e}")
            return []
    
    def _is_valid_text_region(self, width: int, height: int) -> bool:
        """判断是否为有效的文本区域"""
        area = width * height
        aspect_ratio = width / height if height > 0 else 0
        
        return (self.min_text_area <= area <= self.max_text_area and
                self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio)
    
    def _filter_and_merge_regions(self, regions: List[Tuple[int, int, int, int]], 
                                 image_shape: Tuple[int, int]) -> List[Tuple[int, int, int, int]]:
        """过滤和合并重叠的区域"""
        if not regions:
            return []
        
        height, width = image_shape
        
        # 去重和过滤
        unique_regions = []
        for region in regions:
            x, y, w, h = region
            
            # 确保区域在图片范围内
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = min(w, width - x)
            h = min(h, height - y)
            
            if w > 10 and h > 10:  # 最小尺寸过滤
                unique_regions.append((x, y, w, h))
        
        if not unique_regions:
            return []
        
        # 合并重叠区域
        merged_regions = []
        sorted_regions = sorted(unique_regions, key=lambda r: r[0])  # 按x坐标排序
        
        for region in sorted_regions:
            if not merged_regions:
                merged_regions.append(region)
                continue
            
            # 检查是否与最后一个区域重叠
            last_region = merged_regions[-1]
            if self._regions_overlap(region, last_region):
                # 合并区域
                merged_region = self._merge_regions(region, last_region)
                merged_regions[-1] = merged_region
            else:
                merged_regions.append(region)
        
        return merged_regions
    
    def _regions_overlap(self, region1: Tuple[int, int, int, int], 
                        region2: Tuple[int, int, int, int]) -> bool:
        """检查两个区域是否重叠"""
        x1, y1, w1, h1 = region1
        x2, y2, w2, h2 = region2
        
        # 计算重叠面积
        overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        overlap_area = overlap_x * overlap_y
        
        # 如果重叠面积超过较小区域的50%，认为重叠
        min_area = min(w1 * h1, w2 * h2)
        return overlap_area > min_area * 0.5
    
    def _merge_regions(self, region1: Tuple[int, int, int, int], 
                      region2: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """合并两个区域"""
        x1, y1, w1, h1 = region1
        x2, y2, w2, h2 = region2
        
        # 计算合并后的边界框
        min_x = min(x1, x2)
        min_y = min(y1, y2)
        max_x = max(x1 + w1, x2 + w2)
        max_y = max(y1 + h1, y2 + h2)
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    def crop_text_regions(self, image_path: str, padding: int = 20) -> List[str]:
        """裁剪文本区域并保存为临时文件"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            regions = self.detect_text_regions(image_path)
            if not regions:
                # 如果没有检测到区域，返回原图
                return [image_path]
            
            cropped_paths = []
            height, width = img.shape[:2]
            
            for i, (x, y, w, h) in enumerate(regions):
                # 添加padding
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(width, x + w + padding)
                y2 = min(height, y + h + padding)
                
                # 裁剪区域
                cropped = img[y1:y2, x1:x2]
                
                # 保存裁剪的图片
                temp_fd, temp_path = tempfile.mkstemp(suffix=f'_roi_{i}.jpg')
                os.close(temp_fd)
                cv2.imwrite(temp_path, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
                cropped_paths.append(temp_path)
            
            print(f"裁剪了 {len(cropped_paths)} 个文本区域")
            return cropped_paths
            
        except Exception as e:
            print(f"文本区域裁剪失败: {e}")
            return [image_path]  # 失败时返回原图
    
    def get_stats(self) -> dict:
        """获取ROI检测统计信息"""
        return {
            'min_text_area': self.min_text_area,
            'max_text_area': self.max_text_area,
            'min_aspect_ratio': self.min_aspect_ratio,
            'max_aspect_ratio': self.max_aspect_ratio
        }
