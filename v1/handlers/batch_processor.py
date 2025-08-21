"""
批量处理器模块

提供多线程并行处理、任务队列管理、进度监控等功能
"""

import threading
import queue
import time
import logging
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json

from core.date_recognizer import create_date_recognizer
from core.models import RecognitionResult, BatchResult, create_batch_result
from v1.handlers.file_handler import FileHandler, ProgressTracker, create_file_handler
from utils.config_loader import get_config
from utils.logger import performance_logger

logger = logging.getLogger(__name__)


class BatchProcessingError(Exception):
    """批量处理异常"""
    pass


@dataclass
class ProcessingTask:
    """处理任务数据类"""
    task_id: str
    file_path: str
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ProcessingResult:
    """处理结果数据类"""
    task_id: str
    file_path: str
    result: Optional[RecognitionResult]
    success: bool
    error: Optional[str]
    processing_time: float


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, max_size: int = 1000):
        """初始化任务队列
        
        Args:
            max_size: 队列最大大小
        """
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.lock = threading.Lock()
        self.task_counter = 0
    
    def add_task(self, file_path: str, priority: int = 0) -> str:
        """添加任务
        
        Args:
            file_path: 文件路径
            priority: 优先级（数字越小优先级越高）
            
        Returns:
            任务ID
        """
        with self.lock:
            self.task_counter += 1
            task_id = f"task_{self.task_counter:06d}"
        
        task = ProcessingTask(
            task_id=task_id,
            file_path=file_path,
            priority=priority
        )
        
        # 使用负优先级，因为PriorityQueue是最小堆
        self.queue.put((-priority, task_id, task))
        return task_id
    
    def get_task(self, timeout: Optional[float] = None) -> Optional[ProcessingTask]:
        """获取任务
        
        Args:
            timeout: 超时时间
            
        Returns:
            处理任务，如果队列为空则返回None
        """
        try:
            _, _, task = self.queue.get(timeout=timeout)
            return task
        except queue.Empty:
            return None
    
    def mark_completed(self, task_id: str, result: ProcessingResult):
        """标记任务完成
        
        Args:
            task_id: 任务ID
            result: 处理结果
        """
        with self.lock:
            self.completed_tasks[task_id] = result
    
    def mark_failed(self, task_id: str, result: ProcessingResult):
        """标记任务失败
        
        Args:
            task_id: 任务ID
            result: 处理结果
        """
        with self.lock:
            self.failed_tasks[task_id] = result
    
    def get_stats(self) -> Dict[str, int]:
        """获取队列统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            return {
                'pending': self.queue.qsize(),
                'completed': len(self.completed_tasks),
                'failed': len(self.failed_tasks),
                'total_processed': len(self.completed_tasks) + len(self.failed_tasks)
            }


class BatchProcessor:
    """批量处理器类
    
    提供多线程并行处理、任务队列管理、进度监控等功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化批量处理器
        
        Args:
            config: 配置字典，如果为None则使用全局配置
        """
        if config is None:
            app_config = get_config()
            self.config = app_config.config
        else:
            self.config = config
        
        # 性能配置
        perf_config = self.config.get('performance', {})
        self.max_workers = perf_config.get('max_workers', 4)
        self.batch_size = perf_config.get('batch_size', 10)
        self.single_timeout = perf_config.get('single_image_timeout', 30)
        self.batch_timeout = perf_config.get('batch_timeout', 300)
        
        # 缓存配置
        self.cache_enabled = perf_config.get('cache_enabled', True)
        self.cache_size = perf_config.get('cache_size', 1000)
        
        # 初始化组件
        self.file_handler = create_file_handler(self.config)
        self.date_recognizer = create_date_recognizer(self.config)
        self.task_queue = TaskQueue()
        
        # 结果缓存
        self.result_cache = {} if self.cache_enabled else None
        self.cache_lock = threading.Lock() if self.cache_enabled else None
        
        # 状态管理
        self.is_processing = False
        self.processing_lock = threading.Lock()
        
        logger.info(f"批量处理器初始化完成: {self.max_workers} 工作线程")
    
    def process_files(self, file_paths: List[str], 
                     progress_callback: Optional[Callable] = None) -> BatchResult:
        """批量处理文件
        
        Args:
            file_paths: 文件路径列表
            progress_callback: 进度回调函数
            
        Returns:
            批量处理结果
            
        Raises:
            BatchProcessingError: 批量处理失败
        """
        with self.processing_lock:
            if self.is_processing:
                raise BatchProcessingError("批量处理正在进行中")
            self.is_processing = True
        
        try:
            logger.info(f"开始批量处理: {len(file_paths)} 个文件")
            start_time = time.time()
            
            # 创建批量结果对象
            batch_result = create_batch_result("batch_processing")
            batch_result.total_files = len(file_paths)
            
            # 文件验证
            validation_result = self.file_handler.validate_batch_files(file_paths)
            valid_files = [f['path'] for f in validation_result['valid_files']]
            
            if not valid_files:
                logger.warning("没有有效的文件需要处理")
                batch_result.total_processed = 0
                return batch_result
            
            # 创建进度跟踪器
            progress_tracker = ProgressTracker(len(valid_files))
            if progress_callback:
                progress_tracker.add_callback(progress_callback)
            
            # 执行并行处理
            results = self._process_parallel(valid_files, progress_tracker)
            
            # 统计结果
            processing_time = time.time() - start_time
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            # 更新批量结果
            batch_result.total_processed = len(results)
            batch_result.successful_recognitions = len(successful_results)
            batch_result.failed_recognitions = len(failed_results)
            batch_result.processing_time = processing_time
            batch_result.results = [r.result for r in results if r.result]
            
            # 记录性能指标
            performance_logger.log_batch_performance(
                len(valid_files), processing_time, 
                len(successful_results), len(failed_results)
            )
            
            logger.info(f"批量处理完成: {len(successful_results)}/{len(valid_files)} 成功")

            # 显示OCR引擎统计信息
            try:
                from core.ocr_engine import get_ocr_engine
                ocr_engine = get_ocr_engine()
                engine_info = ocr_engine.get_engine_info()

                if 'ocr_stats' in engine_info:
                    stats = engine_info['ocr_stats']
                    logger.info("OCR引擎使用统计:")
                    for key, value in stats.items():
                        logger.info(f"  {key}: {value}")

            except Exception as e:
                logger.debug(f"获取OCR统计信息失败: {e}")

            return batch_result
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            raise BatchProcessingError(f"批量处理失败: {e}")
        finally:
            with self.processing_lock:
                self.is_processing = False
    
    def _process_parallel(self, file_paths: List[str], 
                         progress_tracker: ProgressTracker) -> List[ProcessingResult]:
        """并行处理文件
        
        Args:
            file_paths: 文件路径列表
            progress_tracker: 进度跟踪器
            
        Returns:
            处理结果列表
        """
        results = []
        
        # 使用线程池执行器
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_path = {
                executor.submit(self._process_single_file, file_path): file_path
                for file_path in file_paths
            }
            
            # 收集结果
            for future in as_completed(future_to_path, timeout=self.batch_timeout):
                file_path = future_to_path[future]
                
                try:
                    result = future.result(timeout=self.single_timeout)
                    results.append(result)
                    
                    # 更新进度
                    progress_tracker.update(1)
                    
                    logger.debug(f"文件处理完成: {file_path}")
                    
                except Exception as e:
                    # 创建失败结果
                    error_result = ProcessingResult(
                        task_id=f"error_{len(results)}",
                        file_path=file_path,
                        result=None,
                        success=False,
                        error=str(e),
                        processing_time=0.0
                    )
                    results.append(error_result)
                    progress_tracker.update(1)
                    
                    logger.error(f"文件处理失败: {file_path}, 错误: {e}")
        
        return results
    
    def _process_single_file(self, file_path: str) -> ProcessingResult:
        """处理单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            处理结果
        """
        start_time = time.time()
        task_id = f"single_{int(time.time() * 1000)}"
        
        try:
            # 检查缓存
            if self.cache_enabled and self._check_cache(file_path):
                cached_result = self._get_from_cache(file_path)
                return ProcessingResult(
                    task_id=task_id,
                    file_path=file_path,
                    result=cached_result,
                    success=True,
                    error=None,
                    processing_time=time.time() - start_time
                )
            
            # 执行识别
            recognition_result = self.date_recognizer.recognize_single(file_path)
            
            # 缓存结果
            if self.cache_enabled:
                self._save_to_cache(file_path, recognition_result)
            
            return ProcessingResult(
                task_id=task_id,
                file_path=file_path,
                result=recognition_result,
                success=recognition_result.success,
                error=recognition_result.warning_message,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return ProcessingResult(
                task_id=task_id,
                file_path=file_path,
                result=None,
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _check_cache(self, file_path: str) -> bool:
        """检查缓存中是否存在结果
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否存在缓存
        """
        if not self.cache_enabled:
            return False
        
        with self.cache_lock:
            return file_path in self.result_cache
    
    def _get_from_cache(self, file_path: str) -> Optional[RecognitionResult]:
        """从缓存获取结果
        
        Args:
            file_path: 文件路径
            
        Returns:
            缓存的识别结果
        """
        if not self.cache_enabled:
            return None
        
        with self.cache_lock:
            return self.result_cache.get(file_path)
    
    def _save_to_cache(self, file_path: str, result: RecognitionResult):
        """保存结果到缓存
        
        Args:
            file_path: 文件路径
            result: 识别结果
        """
        if not self.cache_enabled:
            return
        
        with self.cache_lock:
            # 如果缓存已满，移除最旧的条目
            if len(self.result_cache) >= self.cache_size:
                oldest_key = next(iter(self.result_cache))
                del self.result_cache[oldest_key]
            
            self.result_cache[file_path] = result
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache_enabled:
            with self.cache_lock:
                self.result_cache.clear()
                logger.info("结果缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        if not self.cache_enabled:
            return {'enabled': False}
        
        with self.cache_lock:
            return {
                'enabled': True,
                'size': len(self.result_cache),
                'max_size': self.cache_size,
                'usage_rate': len(self.result_cache) / self.cache_size
            }
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """获取处理器统计信息
        
        Returns:
            处理器统计信息
        """
        return {
            'max_workers': self.max_workers,
            'batch_size': self.batch_size,
            'is_processing': self.is_processing,
            'cache_stats': self.get_cache_stats(),
            'queue_stats': self.task_queue.get_stats()
        }
    
    def stop_processing(self):
        """停止处理（优雅关闭）"""
        logger.info("正在停止批量处理...")
        with self.processing_lock:
            self.is_processing = False


# 工厂函数
def create_batch_processor(config: Optional[Dict] = None) -> BatchProcessor:
    """创建批量处理器实例
    
    Args:
        config: 配置字典
        
    Returns:
        批量处理器实例
    """
    return BatchProcessor(config)
