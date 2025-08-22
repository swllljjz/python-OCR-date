#!/usr/bin/env python3
"""
图片分析工具 - 分析OCR失败的原因并提供优化建议
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
from pathlib import Path


class ImageAnalyzer:
    """图片质量分析器"""
    
    def __init__(self):
        """初始化图片分析器"""
        self.analysis_results = {}
    
    def analyze_image(self, image_path: str) -> Dict:
        """全面分析图片质量和特征"""
        try:
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                return {'error': '无法读取图片文件'}
            
            # 基本信息
            height, width = img.shape[:2]
            channels = img.shape[2] if len(img.shape) > 2 else 1
            file_size = os.path.getsize(image_path)
            
            # 转换为灰度图
            if channels > 1:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # 分析结果
            analysis = {
                'basic_info': {
                    'width': width,
                    'height': height,
                    'channels': channels,
                    'pixels': width * height,
                    'file_size_mb': file_size / (1024 * 1024),
                    'aspect_ratio': width / height if height > 0 else 0
                },
                'quality_metrics': self._analyze_quality(gray),
                'content_analysis': self._analyze_content(gray),
                'preprocessing_suggestions': [],
                'ocr_difficulty': 'unknown'
            }
            
            # 生成预处理建议
            analysis['preprocessing_suggestions'] = self._generate_suggestions(analysis)
            
            # 评估OCR难度
            analysis['ocr_difficulty'] = self._assess_ocr_difficulty(analysis)
            
            return analysis
            
        except Exception as e:
            return {'error': f'图片分析失败: {e}'}
    
    def _analyze_quality(self, gray_img: np.ndarray) -> Dict:
        """分析图片质量指标"""
        try:
            # 亮度统计
            mean_brightness = np.mean(gray_img)
            brightness_std = np.std(gray_img)
            
            # 对比度分析
            contrast = brightness_std
            
            # 清晰度分析（拉普拉斯方差）
            laplacian_var = cv2.Laplacian(gray_img, cv2.CV_64F).var()
            
            # 直方图分析
            hist = cv2.calcHist([gray_img], [0], None, [256], [0, 256])
            hist_peak = np.argmax(hist)
            hist_spread = np.std(np.where(hist > hist.max() * 0.1)[0])
            
            # 边缘密度
            edges = cv2.Canny(gray_img, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            return {
                'mean_brightness': float(mean_brightness),
                'brightness_std': float(brightness_std),
                'contrast': float(contrast),
                'sharpness': float(laplacian_var),
                'hist_peak': int(hist_peak),
                'hist_spread': float(hist_spread),
                'edge_density': float(edge_density)
            }
            
        except Exception as e:
            return {'error': f'质量分析失败: {e}'}
    
    def _analyze_content(self, gray_img: np.ndarray) -> Dict:
        """分析图片内容特征"""
        try:
            # 文本区域检测（简单方法）
            # 使用形态学操作检测可能的文本区域
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            # 二值化
            _, binary = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 形态学操作
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 分析轮廓特征
            text_like_regions = 0
            total_text_area = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # 过滤小区域
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # 判断是否像文本区域
                    if 0.1 < aspect_ratio < 20 and area > 500:
                        text_like_regions += 1
                        total_text_area += area
            
            # 计算文本区域占比
            text_area_ratio = total_text_area / gray_img.size
            
            return {
                'total_contours': len(contours),
                'text_like_regions': text_like_regions,
                'text_area_ratio': float(text_area_ratio),
                'binary_threshold': int(cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0])
            }
            
        except Exception as e:
            return {'error': f'内容分析失败: {e}'}
    
    def _generate_suggestions(self, analysis: Dict) -> List[str]:
        """基于分析结果生成预处理建议"""
        suggestions = []
        
        try:
            quality = analysis.get('quality_metrics', {})
            content = analysis.get('content_analysis', {})
            basic = analysis.get('basic_info', {})
            
            # 亮度问题
            brightness = quality.get('mean_brightness', 128)
            if brightness < 80:
                suggestions.append('图片过暗，建议增加亮度')
            elif brightness > 200:
                suggestions.append('图片过亮，建议降低亮度')
            
            # 对比度问题
            contrast = quality.get('contrast', 50)
            if contrast < 30:
                suggestions.append('对比度过低，建议增强对比度')
            elif contrast > 100:
                suggestions.append('对比度过高，建议使用自适应处理')
            
            # 清晰度问题
            sharpness = quality.get('sharpness', 100)
            if sharpness < 50:
                suggestions.append('图片模糊，建议使用锐化滤波')
            
            # 尺寸问题
            pixels = basic.get('pixels', 0)
            if pixels < 100000:  # 小于100k像素
                suggestions.append('图片尺寸过小，建议放大处理')
            elif pixels > 5000000:  # 大于500万像素
                suggestions.append('图片尺寸过大，建议适当缩小')
            
            # 文本区域问题
            text_regions = content.get('text_like_regions', 0)
            if text_regions == 0:
                suggestions.append('未检测到明显文本区域，建议使用激进预处理')
            elif text_regions > 50:
                suggestions.append('检测到过多文本区域，建议使用ROI过滤')
            
            # 边缘密度问题
            edge_density = quality.get('edge_density', 0)
            if edge_density < 0.01:
                suggestions.append('边缘信息不足，建议增强边缘')
            elif edge_density > 0.1:
                suggestions.append('边缘信息过多，建议降噪处理')
            
            if not suggestions:
                suggestions.append('图片质量良好，使用标准预处理即可')
                
        except Exception as e:
            suggestions.append(f'建议生成失败: {e}')
        
        return suggestions
    
    def _assess_ocr_difficulty(self, analysis: Dict) -> str:
        """评估OCR识别难度"""
        try:
            quality = analysis.get('quality_metrics', {})
            content = analysis.get('content_analysis', {})
            
            # 计算难度分数
            difficulty_score = 0
            
            # 亮度因素
            brightness = quality.get('mean_brightness', 128)
            if brightness < 60 or brightness > 220:
                difficulty_score += 2
            elif brightness < 80 or brightness > 200:
                difficulty_score += 1
            
            # 对比度因素
            contrast = quality.get('contrast', 50)
            if contrast < 20:
                difficulty_score += 2
            elif contrast < 30:
                difficulty_score += 1
            
            # 清晰度因素（更严格的评估）
            sharpness = quality.get('sharpness', 100)
            if sharpness < 50:  # 降低阈值
                difficulty_score += 3  # 增加权重
            elif sharpness < 100:
                difficulty_score += 2
            
            # 文本区域因素
            text_regions = content.get('text_like_regions', 0)
            if text_regions == 0:
                difficulty_score += 2
            elif text_regions > 100:
                difficulty_score += 1
            
            # 边缘密度因素
            edge_density = quality.get('edge_density', 0)
            if edge_density < 0.005:
                difficulty_score += 1
            
            # 评估难度等级（调整阈值）
            if difficulty_score >= 5:  # 降低very_hard阈值
                return 'very_hard'
            elif difficulty_score >= 3:  # 降低hard阈值
                return 'hard'
            elif difficulty_score >= 1:  # 降低medium阈值
                return 'medium'
            else:
                return 'easy'
                
        except Exception as e:
            return 'unknown'
    
    def analyze_failed_file(self, image_path: str) -> Dict:
        """专门分析OCR失败的文件"""
        print(f"\n🔍 分析OCR失败文件: {os.path.basename(image_path)}")
        print("-" * 50)
        
        analysis = self.analyze_image(image_path)
        
        if 'error' in analysis:
            print(f"❌ 分析失败: {analysis['error']}")
            return analysis
        
        # 显示分析结果
        basic = analysis['basic_info']
        quality = analysis['quality_metrics']
        content = analysis['content_analysis']
        
        print(f"📏 基本信息:")
        print(f"   尺寸: {basic['width']}x{basic['height']} ({basic['pixels']:,}像素)")
        print(f"   文件大小: {basic['file_size_mb']:.2f}MB")
        print(f"   宽高比: {basic['aspect_ratio']:.2f}")
        
        print(f"\n📊 质量指标:")
        print(f"   平均亮度: {quality['mean_brightness']:.1f} (理想: 80-200)")
        print(f"   对比度: {quality['contrast']:.1f} (理想: 30-100)")
        print(f"   清晰度: {quality['sharpness']:.1f} (理想: >50)")
        print(f"   边缘密度: {quality['edge_density']:.3f} (理想: 0.01-0.1)")
        
        print(f"\n📝 内容分析:")
        print(f"   文本区域数: {content['text_like_regions']}")
        print(f"   文本面积占比: {content['text_area_ratio']:.3f}")
        print(f"   二值化阈值: {content['binary_threshold']}")
        
        print(f"\n🎯 OCR难度: {analysis['ocr_difficulty']}")
        
        print(f"\n💡 预处理建议:")
        for i, suggestion in enumerate(analysis['preprocessing_suggestions'], 1):
            print(f"   {i}. {suggestion}")
        
        return analysis
    
    def get_optimization_strategy(self, analysis: Dict) -> str:
        """根据分析结果推荐优化策略"""
        if 'error' in analysis:
            return 'standard'
        
        difficulty = analysis.get('ocr_difficulty', 'medium')
        
        if difficulty == 'very_hard':
            return 'super_aggressive'
        elif difficulty == 'hard':
            return 'aggressive'
        elif difficulty == 'medium':
            return 'enhanced'
        else:
            return 'standard'
