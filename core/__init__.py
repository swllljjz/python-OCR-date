"""
核心引擎模块

包含OCR识别、图像处理、日期解析等核心功能
"""

__version__ = "1.0.0"
__author__ = "OCR Date Recognition Team"

# 核心组件导入 - 延迟导入避免循环依赖
__all__ = [
    # 数据模型
    'RecognitionResult',
    'BatchResult',
    'TextResult',
    'DateInfo',
    'create_recognition_result',
    'create_batch_result',
    # 核心组件
    'ImageProcessor',
    'OCREngine',
    'DateParser',
    'DateRecognizer',
    # 工厂函数
    'create_image_processor',
    'create_ocr_engine',
    'create_date_parser',
    'create_date_recognizer'
]

def __getattr__(name):
    """延迟导入核心组件"""
    if name in ['RecognitionResult', 'BatchResult', 'TextResult', 'DateInfo',
                'create_recognition_result', 'create_batch_result']:
        from .models import (
            RecognitionResult, BatchResult, TextResult, DateInfo,
            create_recognition_result, create_batch_result
        )
        return locals()[name]
    elif name in ['ImageProcessor', 'create_image_processor']:
        from .image_processor import ImageProcessor, create_image_processor
        return locals()[name]
    elif name in ['OCREngine', 'create_ocr_engine']:
        from .ocr_engine import OCREngine, create_ocr_engine
        return locals()[name]
    elif name in ['DateParser', 'create_date_parser']:
        from .date_parser import DateParser, create_date_parser
        return locals()[name]
    elif name in ['DateRecognizer', 'create_date_recognizer']:
        from .date_recognizer import DateRecognizer, create_date_recognizer
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
