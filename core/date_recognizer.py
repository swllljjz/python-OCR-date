"""
日期识别器模块

提供统一的日期识别接口，整合图像处理、OCR识别和日期解析功能
"""

import time
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import numpy as np

from .models import RecognitionResult, BatchResult, create_recognition_result, create_batch_result
from .image_processor import ImageProcessor, create_image_processor
from .ocr_engine import OCREngine, create_ocr_engine
from .date_parser import DateParser, create_date_parser
from utils.config_loader import get_config
from utils.validators import validate_image_file, validate_directory
from utils.logger import timing_decorator, performance_logger

logger = logging.getLogger(__name__)


class DateRecognitionError(Exception):
    """日期识别异常"""
    pass


class DateRecognizer:
    """统一的日期识别接口类
    
    整合图像处理、OCR识别和日期解析功能，提供完整的日期识别服务
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化日期识别器
        
        Args:
            config: 配置字典，如果为None则使用全局配置
        """
        self.config = config or get_config().config
        
        # 初始化各个组件
        self.image_processor = create_image_processor(self.config)
        self.ocr_engine = create_ocr_engine(self.config)
        self.date_parser = create_date_parser(self.config)
        
        # 预警配置
        warning_config = self.config.get('warning', {})
        self.enable_warnings = {
            'no_date_found': warning_config.get('no_date_found', True),
            'invalid_date': warning_config.get('invalid_date', True),
            'low_confidence': warning_config.get('low_confidence', True),
            'processing_error': warning_config.get('processing_error', True)
        }
        self.low_confidence_threshold = warning_config.get('low_confidence_threshold', 0.6)
        
        logger.info("日期识别器初始化完成")
    
    @timing_decorator
    def recognize_single(self, image_path: str) -> RecognitionResult:
        """识别单张图片中的日期
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            识别结果对象
            
        Raises:
            DateRecognitionError: 识别过程中的错误
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始识别图片: {image_path}")
            
            # 1. 加载和预处理图像
            image = self.image_processor.load_image(image_path)
            image_info = self.image_processor.get_image_info(image)
            processed_image = self.image_processor.preprocess_image(image)
            
            # 2. OCR文本识别
            text_results = self.ocr_engine.recognize_text(processed_image)
            
            # 3. 日期解析
            date_infos = self.date_parser.parse_dates_from_text(text_results)
            
            # 4. 构建识别结果
            processing_time = time.time() - start_time
            result = self._build_recognition_result(
                image_path, text_results, date_infos, 
                processing_time, image_info['width'], image_info['height']
            )
            
            logger.info(f"图片识别完成: {image_path}, 找到 {len(result.dates_found)} 个日期")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"图片识别失败: {image_path}, 错误: {e}")
            
            # 创建失败结果
            result = create_recognition_result(image_path, False, processing_time)
            result.warning_message = f"识别失败: {str(e)}"
            
            if self.enable_warnings['processing_error']:
                logger.warning(f"处理错误预警: {image_path}")
            
            return result
    
    def recognize_batch(self, image_paths: List[str], 
                       max_workers: int = 4) -> List[RecognitionResult]:
        """批量识别多张图片
        
        Args:
            image_paths: 图片文件路径列表
            max_workers: 最大并行工作线程数
            
        Returns:
            识别结果列表
        """
        results = []
        
        try:
            logger.info(f"开始批量识别: {len(image_paths)} 张图片")
            start_time = time.time()
            
            # 简单的顺序处理（后续可以改为并行处理）
            for i, image_path in enumerate(image_paths):
                try:
                    result = self.recognize_single(image_path)
                    results.append(result)
                    
                    # 进度日志
                    if (i + 1) % 10 == 0:
                        logger.info(f"批量处理进度: {i + 1}/{len(image_paths)}")
                        
                except Exception as e:
                    logger.error(f"批量处理中单张图片失败: {image_path}, 错误: {e}")
                    # 创建失败结果
                    failed_result = create_recognition_result(image_path, False)
                    failed_result.warning_message = f"处理失败: {str(e)}"
                    results.append(failed_result)
            
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.success)
            
            # 记录批量处理性能
            performance_logger.log_batch_performance(
                len(image_paths), total_time, success_count, 
                len(image_paths) - success_count
            )
            
            logger.info(f"批量识别完成: {success_count}/{len(image_paths)} 成功")
            return results
            
        except Exception as e:
            logger.error(f"批量识别失败: {e}")
            raise DateRecognitionError(f"批量识别失败: {e}")
    
    def recognize_folder(self, folder_path: str, 
                        recursive: bool = True,
                        file_extensions: Optional[List[str]] = None) -> BatchResult:
        """识别文件夹中的所有图片
        
        Args:
            folder_path: 文件夹路径
            recursive: 是否递归扫描子文件夹
            file_extensions: 支持的文件扩展名
            
        Returns:
            批量处理结果对象
        """
        try:
            logger.info(f"开始识别文件夹: {folder_path}")
            
            # 验证文件夹
            validate_directory(folder_path)
            
            # 扫描图片文件
            image_files = self._scan_image_files(folder_path, recursive, file_extensions)
            
            if not image_files:
                logger.warning(f"文件夹中未找到图片文件: {folder_path}")
            
            # 创建批量结果对象
            batch_result = create_batch_result(folder_path)
            batch_result.total_files = len(image_files)
            
            # 批量识别
            start_time = time.time()
            results = self.recognize_batch(image_files)
            processing_time = time.time() - start_time
            
            # 统计结果
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            # 更新批量结果
            batch_result.total_processed = len(results)
            batch_result.successful_recognitions = len(successful_results)
            batch_result.failed_recognitions = len(failed_results)
            batch_result.processing_time = processing_time
            batch_result.results = results
            
            logger.info(f"文件夹识别完成: {folder_path}, 成功率: {batch_result.success_rate:.2%}")
            return batch_result
            
        except Exception as e:
            logger.error(f"文件夹识别失败: {folder_path}, 错误: {e}")
            raise DateRecognitionError(f"文件夹识别失败: {e}")
    
    def _scan_image_files(self, folder_path: str, recursive: bool,
                         file_extensions: Optional[List[str]]) -> List[str]:
        """扫描文件夹中的图片文件
        
        Args:
            folder_path: 文件夹路径
            recursive: 是否递归扫描
            file_extensions: 支持的文件扩展名
            
        Returns:
            图片文件路径列表
        """
        if file_extensions is None:
            file_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        # 转换为小写以便比较
        file_extensions = [ext.lower() for ext in file_extensions]
        
        image_files = []
        folder = Path(folder_path)
        
        try:
            if recursive:
                # 递归扫描
                for file_path in folder.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                        image_files.append(str(file_path))
            else:
                # 只扫描当前目录
                for file_path in folder.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                        image_files.append(str(file_path))
            
            # 排序以确保一致的处理顺序
            image_files.sort()
            
            logger.debug(f"扫描到 {len(image_files)} 个图片文件")
            return image_files
            
        except Exception as e:
            logger.error(f"文件扫描失败: {folder_path}, 错误: {e}")
            return []
    
    def _build_recognition_result(self, image_path: str, text_results: List,
                                date_infos: List, processing_time: float,
                                width: int, height: int) -> RecognitionResult:
        """构建识别结果对象
        
        Args:
            image_path: 图片路径
            text_results: OCR文本结果
            date_infos: 日期信息列表
            processing_time: 处理时间
            width: 图片宽度
            height: 图片高度
            
        Returns:
            识别结果对象
        """
        # 提取日期列表
        dates_found = [info.parsed_date for info in date_infos if info.parsed_date]
        
        # 计算整体置信度
        if date_infos:
            confidence = max(info.confidence for info in date_infos)
        else:
            confidence = 0.0
        
        # 提取原始文本
        raw_text = [result.text for result in text_results]
        
        # 判断是否成功
        success = len(dates_found) > 0
        
        # 生成警告信息
        warning_message = self._generate_warning_message(
            success, dates_found, confidence, text_results
        )
        
        # 创建结果对象
        result = RecognitionResult(
            image_path=image_path,
            success=success,
            dates_found=dates_found,
            confidence=confidence,
            processing_time=processing_time,
            warning_message=warning_message,
            raw_text=raw_text,
            image_size=(width, height),
            date_details=date_infos,
            ocr_results=text_results
        )
        
        return result
    
    def _generate_warning_message(self, success: bool, dates_found: List[str],
                                confidence: float, text_results: List) -> Optional[str]:
        """生成警告信息
        
        Args:
            success: 是否识别成功
            dates_found: 找到的日期列表
            confidence: 置信度
            text_results: OCR文本结果
            
        Returns:
            警告信息，无警告返回None
        """
        warnings = []
        
        # 检查是否找到日期
        if not success and self.enable_warnings['no_date_found']:
            if not text_results:
                warnings.append("未识别到任何文本")
            else:
                warnings.append("未在识别的文本中找到日期信息")
        
        # 检查置信度
        if success and confidence < self.low_confidence_threshold:
            if self.enable_warnings['low_confidence']:
                warnings.append(f"识别置信度较低: {confidence:.2f}")
        
        # 检查日期有效性
        if dates_found and self.enable_warnings['invalid_date']:
            invalid_dates = []
            for date_str in dates_found:
                if not self.date_parser.validate_date(date_str):
                    invalid_dates.append(date_str)
            
            if invalid_dates:
                warnings.append(f"发现无效日期: {', '.join(invalid_dates)}")
        
        return "; ".join(warnings) if warnings else None
    
    def get_recognizer_info(self) -> Dict[str, Any]:
        """获取识别器信息
        
        Returns:
            识别器信息字典
        """
        return {
            'image_processor': self.image_processor.config,
            'ocr_engine': self.ocr_engine.get_engine_info(),
            'date_parser': self.date_parser.get_parser_info(),
            'warning_settings': self.enable_warnings,
            'low_confidence_threshold': self.low_confidence_threshold
        }
    
    def warmup(self):
        """预热识别器
        
        执行一次完整的识别流程来预热所有组件
        """
        try:
            logger.info("开始识别器预热...")
            start_time = time.time()
            
            # 创建测试图像
            test_image = np.ones((200, 400, 3), dtype=np.uint8) * 255
            # 添加一些模拟的日期文本区域
            test_image[50:100, 50:350] = 0  # 黑色文本区域
            
            # 预热OCR引擎
            self.ocr_engine.warmup(test_image)
            
            warmup_time = time.time() - start_time
            logger.info(f"识别器预热完成，耗时: {warmup_time:.3f}秒")
            
        except Exception as e:
            logger.warning(f"识别器预热失败: {e}")


# 工厂函数
def create_date_recognizer(config: Optional[Dict] = None) -> DateRecognizer:
    """创建日期识别器实例
    
    Args:
        config: 配置字典
        
    Returns:
        日期识别器实例
    """
    return DateRecognizer(config)
