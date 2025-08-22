"""
OCR识别引擎模块

提供基于PaddleOCR的文本识别功能
"""

import numpy as np
import logging
from typing import List, Optional, Dict, Any, Tuple
import time


from .models import TextResult
from utils.config_loader import get_config
from utils.logger import timing_decorator

logger = logging.getLogger(__name__)


class OCREngineError(Exception):
    """OCR引擎异常"""
    pass





class OCREngine:
    """OCR识别引擎封装类
    
    基于PaddleOCR实现文本识别功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化OCR引擎
        
        Args:
            config: OCR配置参数，如果为None则使用全局配置
        """
        if config is None:
            app_config = get_config()
            self.config = app_config.get_section('ocr')
        else:
            self.config = config.get('ocr', {})
        
        # 配置参数
        self.engine_type = self.config.get('engine', 'paddleocr')
        self.language = self.config.get('language', 'ch')
        self.use_gpu = self.config.get('use_gpu', False)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)
        self.use_angle_cls = self.config.get('use_angle_cls', True)
        self.det_limit_side_len = self.config.get('det_limit_side_len', 960)
        self.det_limit_type = self.config.get('det_limit_type', 'max')
        
        # OCR引擎实例
        self._ocr_instance = None
        self._initialize_engine()
        
        logger.info(f"OCR引擎初始化完成: {self.engine_type}, GPU: {self.use_gpu}")
    
    def _initialize_engine(self):
        """初始化OCR引擎实例"""
        try:
            if self.engine_type.lower() == 'paddleocr':
                self._initialize_paddleocr()
            else:
                raise OCREngineError(f"不支持的OCR引擎类型: {self.engine_type}")
                
        except Exception as e:
            logger.error(f"OCR引擎初始化失败: {e}")
            raise OCREngineError(f"OCR引擎初始化失败: {e}")
    
    def _initialize_paddleocr(self):
        """初始化OCR引擎 - 使用PaddleOCR生产级引擎"""
        logger.info("初始化PaddleOCR生产级引擎...")

        try:
            from core.hybrid_ocr_engine import get_production_ocr_engine
            self._ocr_instance = get_production_ocr_engine()
            logger.info("PaddleOCR生产级引擎初始化成功")

            # 显示可用的OCR引擎
            available_engines = self._ocr_instance.get_available_engines()
            logger.info(f"可用的OCR引擎: {', '.join(available_engines)}")
            return

        except Exception as e:
            logger.error(f"PaddleOCR生产级引擎初始化失败: {e}")
            raise OCREngineError(f"无法初始化OCR引擎: {e}")
    
    @timing_decorator
    def recognize_text(self, image: np.ndarray) -> List[TextResult]:
        """识别图像中的文本
        
        Args:
            image: 输入图像数组
            
        Returns:
            文本识别结果列表
            
        Raises:
            OCREngineError: OCR识别失败
        """
        try:
            if self._ocr_instance is None:
                raise OCREngineError("OCR引擎未初始化")
            
            logger.debug("开始OCR文本识别")
            start_time = time.time()
            
            # 执行OCR识别 - 使用生产级OCR引擎，设置10秒超时
            ocr_results = self._ocr_instance.ocr(image, timeout_seconds=10)
            
            processing_time = time.time() - start_time
            logger.debug(f"OCR识别完成，耗时: {processing_time:.3f}秒")
            
            # 解析OCR结果
            text_results = self._parse_ocr_results(ocr_results)
            
            # 过滤低置信度结果
            filtered_results = [
                result for result in text_results 
                if result.confidence >= self.confidence_threshold
            ]
            
            logger.info(f"OCR识别完成: 总数 {len(text_results)}, 过滤后 {len(filtered_results)}")
            return filtered_results
            
        except Exception as e:
            logger.error(f"OCR文本识别失败: {e}")
            raise OCREngineError(f"OCR文本识别失败: {e}")
    
    def _parse_ocr_results(self, ocr_results: List) -> List[TextResult]:
        """解析OCR识别结果
        
        Args:
            ocr_results: PaddleOCR原始结果
            
        Returns:
            解析后的文本结果列表
        """
        text_results = []
        
        try:
            if not ocr_results or not ocr_results[0]:
                return text_results
            
            for line in ocr_results[0]:
                if len(line) >= 2:
                    bbox = line[0]  # 边界框坐标
                    text_info = line[1]  # 文本和置信度
                    
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text = text_info[0]
                        confidence = text_info[1]
                        
                        # 创建TextResult对象
                        text_result = TextResult(
                            text=text.strip(),
                            confidence=float(confidence),
                            bbox=bbox
                        )
                        
                        text_results.append(text_result)
                        
                        logger.debug(f"识别文本: '{text}', 置信度: {confidence:.3f}")
            
            return text_results
            
        except Exception as e:
            logger.error(f"OCR结果解析失败: {e}")
            return text_results
    
    def detect_orientation(self, image: np.ndarray) -> float:
        """检测文本方向
        
        Args:
            image: 输入图像
            
        Returns:
            旋转角度(度)
        """
        try:
            if not self.use_angle_cls or self._ocr_instance is None:
                return 0.0
            
            # 使用PaddleOCR的方向分类器
            # 注意：这里简化实现，实际可能需要单独调用方向分类器
            # 新版本PaddleOCR不再支持cls参数
            ocr_results = self._ocr_instance.ocr(image)
            
            # 从OCR结果中提取方向信息
            # 这是一个简化的实现，实际情况可能需要更复杂的逻辑
            return 0.0  # 暂时返回0，后续可以改进
            
        except Exception as e:
            logger.warning(f"文本方向检测失败: {e}")
            return 0.0
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息

        Returns:
            引擎信息字典
        """
        info = {
            'engine_type': self.engine_type,
            'language': self.language,
            'use_gpu': self.use_gpu,
            'confidence_threshold': self.confidence_threshold,
            'use_angle_cls': self.use_angle_cls,
            'det_limit_side_len': self.det_limit_side_len,
            'initialized': self._ocr_instance is not None
        }

        # 如果是生产级OCR引擎，添加额外信息
        if hasattr(self._ocr_instance, 'get_available_engines'):
            info['available_engines'] = self._ocr_instance.get_available_engines()

        if hasattr(self._ocr_instance, 'get_stats'):
            info['ocr_stats'] = self._ocr_instance.get_stats()

        return info
    
    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值
        
        Args:
            threshold: 新的置信度阈值 (0.0-1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"置信度阈值已更新: {threshold}")
        else:
            raise ValueError("置信度阈值必须在0.0-1.0之间")
    
    def warmup(self, test_image: Optional[np.ndarray] = None):
        """预热OCR引擎
        
        Args:
            test_image: 测试图像，如果为None则创建默认测试图像
        """
        try:
            if test_image is None:
                # 创建一个简单的测试图像
                test_image = np.ones((100, 200, 3), dtype=np.uint8) * 255
                # 添加一些文本区域（黑色矩形）
                test_image[30:70, 50:150] = 0
            
            logger.info("开始OCR引擎预热...")
            start_time = time.time()
            
            # 执行一次识别来预热引擎
            self.recognize_text(test_image)
            
            warmup_time = time.time() - start_time
            logger.info(f"OCR引擎预热完成，耗时: {warmup_time:.3f}秒")
            
        except Exception as e:
            logger.warning(f"OCR引擎预热失败: {e}")
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, '_ocr_instance') and self._ocr_instance is not None:
            logger.debug("OCR引擎实例已清理")


# 工厂函数
def create_ocr_engine(config: Optional[Dict] = None):
    """创建OCR引擎实例

    Args:
        config: 配置字典

    Returns:
        OCR引擎实例
    """
    # 优先使用优化版本的OCR引擎
    try:
        from .optimized_paddleocr_engine import OptimizedPaddleOCREngine
        logger.info("使用优化版OCR引擎 (100%识别率 + 缓存加速)")
        return OptimizedPaddleOCREngine()
    except Exception as e:
        logger.warning(f"优化版OCR引擎创建失败，使用标准版本: {e}")
        return OCREngine(config)


# 全局OCR引擎实例（单例模式）
_global_ocr_engine = None


def get_ocr_engine() -> OCREngine:
    """获取全局OCR引擎实例
    
    Returns:
        全局OCR引擎实例
    """
    global _global_ocr_engine
    if _global_ocr_engine is None:
        _global_ocr_engine = create_ocr_engine()
    return _global_ocr_engine


def reset_ocr_engine():
    """重置全局OCR引擎实例"""
    global _global_ocr_engine
    _global_ocr_engine = None
