"""
生产级OCR引擎 - 仅使用真正的OCR，不使用任何模拟OCR
"""

import time
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ProductionOCREngine:
    """生产级OCR引擎

    仅使用真正的OCR引擎，不使用任何模拟OCR
    适用于生产环境，确保识别结果的真实性
    """
    
    def __init__(self):
        """初始化生产级OCR引擎"""
        self.real_ocr = None
        self.smart_mock_ocr = None
        self.fallback_ocr = None
        
        # 初始化各种OCR引擎
        self._initialize_engines()
        
        # 统计信息
        self.stats = {
            'real_ocr_success': 0,
            'real_ocr_timeout': 0,
            'real_ocr_error': 0,
            'real_ocr_no_text': 0
        }
    
    def _initialize_engines(self):
        """初始化OCR引擎 - 优先使用PaddleOCR"""
        self.paddle_ocr = None
        self.easy_ocr = None

        # 1. 优先尝试优化的PaddleOCR引擎
        try:
            from core.optimized_paddleocr_engine import OptimizedPaddleOCREngine
            self.paddle_ocr = OptimizedPaddleOCREngine()
            logger.info("优化的PaddleOCR引擎初始化成功")
        except Exception as e:
            logger.warning(f"优化的PaddleOCR引擎初始化失败，尝试标准版本: {e}")
            try:
                from core.paddleocr_engine import PaddleOCREngine
                self.paddle_ocr = PaddleOCREngine()
                logger.info("标准PaddleOCR引擎初始化成功")
            except Exception as e2:
                logger.warning(f"标准PaddleOCR引擎也初始化失败: {e2}")

        # 2. 备选：EasyOCR
        if self.paddle_ocr is None:
            try:
                from core.real_ocr_engine import RealOCREngine
                self.easy_ocr = RealOCREngine()
                logger.info("EasyOCR引擎初始化成功")
            except Exception as e:
                logger.error(f"EasyOCR引擎初始化失败: {e}")

        # 检查是否有可用的OCR引擎
        if self.paddle_ocr is None and self.easy_ocr is None:
            raise Exception("无法初始化任何OCR引擎")
    
    def ocr(self, image, timeout_seconds=None):
        """智能OCR识别 - 优先使用PaddleOCR

        Args:
            image: 输入图像（文件路径或numpy数组）
            timeout_seconds: OCR超时时间

        Returns:
            OCR识别结果
        """
        start_time = time.time()

        # 1. 优先使用PaddleOCR
        if self.paddle_ocr is not None:
            try:
                logger.info("使用PaddleOCR引擎进行识别...")
                results = self.paddle_ocr.ocr(image, timeout_seconds)

                # 检查结果是否有效
                if results and results[0] and len(results[0]) > 0:
                    self.stats['real_ocr_success'] += 1
                    processing_time = time.time() - start_time
                    logger.info(f"PaddleOCR识别成功: 找到 {len(results[0])} 个文本区域 (耗时: {processing_time:.2f}秒)")
                    return results
                else:
                    logger.info("PaddleOCR未识别到文本，尝试EasyOCR...")

            except Exception as e:
                logger.warning(f"PaddleOCR识别失败: {e}")

        # 2. 备选：使用EasyOCR
        if self.easy_ocr is not None:
            try:
                logger.info("使用EasyOCR引擎进行识别...")
                results = self.easy_ocr.ocr(image, timeout_seconds)

                # 检查结果是否有效
                if results and results[0] and len(results[0]) > 0:
                    self.stats['real_ocr_success'] += 1
                    processing_time = time.time() - start_time
                    logger.info(f"EasyOCR识别成功: 找到 {len(results[0])} 个文本区域 (耗时: {processing_time:.2f}秒)")
                    return results
                else:
                    self.stats['real_ocr_no_text'] += 1
                    processing_time = time.time() - start_time
                    logger.warning(f"所有OCR引擎都未识别到文本 (耗时: {processing_time:.2f}秒)")
                    return [[]]

            except Exception as e:
                processing_time = time.time() - start_time
                if "超时" in str(e):
                    self.stats['real_ocr_timeout'] += 1
                    logger.warning(f"OCR识别超时 (耗时: {processing_time:.2f}秒): {e}")
                else:
                    self.stats['real_ocr_error'] += 1
                    logger.warning(f"OCR识别失败 (耗时: {processing_time:.2f}秒): {e}")
                return [[]]
        else:
            logger.error("没有可用的OCR引擎")
            return [[]]
    
    def get_stats(self):
        """获取统计信息"""
        total = sum(self.stats.values())
        if total == 0:
            return self.stats
        
        stats_with_percentage = {}
        for key, value in self.stats.items():
            percentage = (value / total) * 100
            stats_with_percentage[key] = f"{value} ({percentage:.1f}%)"
        
        return stats_with_percentage
    
    def reset_stats(self):
        """重置统计信息"""
        for key in self.stats:
            self.stats[key] = 0
    
    def get_available_engines(self):
        """获取可用的OCR引擎列表"""
        engines = []
        if self.paddle_ocr is not None:
            engines.append("优化PaddleOCR (推荐)")
        if self.easy_ocr is not None:
            engines.append("EasyOCR (备选)")
        return engines


# 全局生产级OCR引擎实例
_global_production_ocr = None

def get_production_ocr_engine():
    """获取全局生产级OCR引擎实例"""
    global _global_production_ocr
    if _global_production_ocr is None:
        _global_production_ocr = ProductionOCREngine()
    return _global_production_ocr

def reset_production_ocr_engine():
    """重置全局生产级OCR引擎实例"""
    global _global_production_ocr
    _global_production_ocr = None
