"""
文件处理模块

提供文件验证、路径处理、批量扫描等功能
"""

import os
import logging
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import threading
import time

from utils.config_loader import get_config
from utils.validators import validate_image_file, validate_directory, is_valid_image_extension

logger = logging.getLogger(__name__)


class FileHandlingError(Exception):
    """文件处理异常"""
    pass


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int = 0):
        """初始化进度跟踪器
        
        Args:
            total: 总任务数
        """
        self.total = total
        self.current = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.callbacks = []
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加进度回调函数
        
        Args:
            callback: 回调函数，接收进度信息字典
        """
        self.callbacks.append(callback)
    
    def update(self, increment: int = 1):
        """更新进度
        
        Args:
            increment: 增量
        """
        with self.lock:
            self.current += increment
            self._notify_callbacks()
    
    def set_total(self, total: int):
        """设置总数
        
        Args:
            total: 总任务数
        """
        with self.lock:
            self.total = total
            self._notify_callbacks()
    
    def reset(self):
        """重置进度"""
        with self.lock:
            self.current = 0
            self.start_time = time.time()
            self._notify_callbacks()
    
    def _notify_callbacks(self):
        """通知所有回调函数"""
        progress_info = self.get_progress_info()
        for callback in self.callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                logger.warning(f"进度回调函数执行失败: {e}")
    
    def get_progress_info(self) -> Dict[str, Any]:
        """获取进度信息
        
        Returns:
            进度信息字典
        """
        elapsed_time = time.time() - self.start_time
        
        if self.total > 0:
            percentage = (self.current / self.total) * 100
            if self.current > 0:
                estimated_total_time = elapsed_time * (self.total / self.current)
                remaining_time = estimated_total_time - elapsed_time
            else:
                estimated_total_time = 0
                remaining_time = 0
        else:
            percentage = 0
            estimated_total_time = 0
            remaining_time = 0
        
        return {
            'current': self.current,
            'total': self.total,
            'percentage': percentage,
            'elapsed_time': elapsed_time,
            'estimated_total_time': estimated_total_time,
            'remaining_time': remaining_time,
            'is_complete': self.current >= self.total and self.total > 0
        }


class FileHandler:
    """文件处理器类
    
    负责文件验证、路径处理、批量扫描等功能
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化文件处理器
        
        Args:
            config: 配置字典，如果为None则使用全局配置
        """
        if config is None:
            app_config = get_config()
            self.config = app_config.config
        else:
            self.config = config
        
        # 图像处理配置
        image_config = self.config.get('image_processing', {})
        self.supported_formats = image_config.get('supported_formats', 
                                                ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'])
        
        # 性能配置
        perf_config = self.config.get('performance', {})
        self.max_file_size = perf_config.get('max_memory_usage', 2048) * 1024 * 1024  # MB转字节
        
        logger.info("文件处理器初始化完成")
    
    def validate_single_file(self, file_path: str) -> Dict[str, Any]:
        """验证单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            验证结果字典
        """
        result = {
            'path': file_path,
            'valid': False,
            'error': None,
            'size': 0,
            'format': None
        }
        
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                result['error'] = "文件不存在"
                return result
            
            # 检查是否为文件
            if not os.path.isfile(file_path):
                result['error'] = "路径不是文件"
                return result
            
            # 获取文件信息
            file_stat = os.stat(file_path)
            result['size'] = file_stat.st_size
            
            # 检查文件大小
            if result['size'] == 0:
                result['error'] = "文件为空"
                return result
            
            if result['size'] > self.max_file_size:
                result['error'] = f"文件过大: {result['size'] / 1024 / 1024:.1f}MB"
                return result
            
            # 检查文件格式
            file_ext = Path(file_path).suffix.lower()
            if not is_valid_image_extension(file_path, self.supported_formats):
                result['error'] = f"不支持的文件格式: {file_ext}"
                return result
            
            result['format'] = file_ext
            
            # 使用验证器进行详细验证
            validate_image_file(file_path, self.supported_formats)
            
            result['valid'] = True
            logger.debug(f"文件验证通过: {file_path}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.debug(f"文件验证失败: {file_path}, 错误: {e}")
        
        return result
    
    def validate_batch_files(self, file_paths: List[str], 
                           progress_tracker: Optional[ProgressTracker] = None) -> Dict[str, Any]:
        """批量验证文件
        
        Args:
            file_paths: 文件路径列表
            progress_tracker: 进度跟踪器
            
        Returns:
            批量验证结果字典
        """
        if progress_tracker:
            progress_tracker.set_total(len(file_paths))
            progress_tracker.reset()
        
        valid_files = []
        invalid_files = []
        total_size = 0
        
        for file_path in file_paths:
            validation_result = self.validate_single_file(file_path)
            
            if validation_result['valid']:
                valid_files.append(validation_result)
                total_size += validation_result['size']
            else:
                invalid_files.append(validation_result)
            
            if progress_tracker:
                progress_tracker.update(1)
        
        result = {
            'total_files': len(file_paths),
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'valid_count': len(valid_files),
            'invalid_count': len(invalid_files),
            'total_size': total_size,
            'total_size_mb': total_size / 1024 / 1024
        }
        
        logger.info(f"批量验证完成: {result['valid_count']}/{result['total_files']} 有效")
        return result
    
    def scan_directory(self, directory_path: str, 
                      recursive: bool = True,
                      progress_tracker: Optional[ProgressTracker] = None) -> List[str]:
        """扫描目录中的图像文件
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归扫描子目录
            progress_tracker: 进度跟踪器
            
        Returns:
            图像文件路径列表
            
        Raises:
            FileHandlingError: 目录扫描失败
        """
        try:
            # 验证目录
            validate_directory(directory_path)
            
            logger.info(f"开始扫描目录: {directory_path}, 递归: {recursive}")
            
            image_files = []
            directory = Path(directory_path)
            
            # 获取所有文件（用于进度跟踪）
            if progress_tracker:
                all_files = []
                if recursive:
                    all_files = list(directory.rglob('*'))
                else:
                    all_files = list(directory.iterdir())
                
                progress_tracker.set_total(len(all_files))
                progress_tracker.reset()
            
            # 扫描文件
            if recursive:
                file_iterator = directory.rglob('*')
            else:
                file_iterator = directory.iterdir()
            
            for file_path in file_iterator:
                if progress_tracker:
                    progress_tracker.update(1)
                
                if file_path.is_file():
                    if is_valid_image_extension(str(file_path), self.supported_formats):
                        image_files.append(str(file_path.resolve()))
            
            # 排序确保一致性
            image_files.sort()
            
            logger.info(f"目录扫描完成: 找到 {len(image_files)} 个图像文件")
            return image_files
            
        except Exception as e:
            logger.error(f"目录扫描失败: {directory_path}, 错误: {e}")
            raise FileHandlingError(f"目录扫描失败: {e}")
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件详细信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        try:
            file_stat = os.stat(file_path)
            file_path_obj = Path(file_path)
            
            return {
                'path': str(file_path_obj.resolve()),
                'name': file_path_obj.name,
                'stem': file_path_obj.stem,
                'suffix': file_path_obj.suffix,
                'size': file_stat.st_size,
                'size_mb': file_stat.st_size / 1024 / 1024,
                'modified_time': file_stat.st_mtime,
                'created_time': file_stat.st_ctime,
                'is_valid_image': is_valid_image_extension(file_path, self.supported_formats)
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {file_path}, 错误: {e}")
            return {
                'path': file_path,
                'error': str(e)
            }
    
    def organize_files_by_format(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """按格式组织文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            按格式分组的文件字典
        """
        organized = {}
        
        for file_path in file_paths:
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in organized:
                organized[file_ext] = []
            organized[file_ext].append(file_path)
        
        return organized
    
    def filter_files_by_size(self, file_paths: List[str], 
                           min_size: int = 0, 
                           max_size: Optional[int] = None) -> List[str]:
        """按文件大小过滤文件
        
        Args:
            file_paths: 文件路径列表
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节），None表示无限制
            
        Returns:
            过滤后的文件路径列表
        """
        filtered_files = []
        
        for file_path in file_paths:
            try:
                file_size = os.path.getsize(file_path)
                if file_size >= min_size:
                    if max_size is None or file_size <= max_size:
                        filtered_files.append(file_path)
            except OSError:
                logger.warning(f"无法获取文件大小: {file_path}")
                continue
        
        return filtered_files
    
    def get_directory_stats(self, directory_path: str, recursive: bool = True) -> Dict[str, Any]:
        """获取目录统计信息
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归统计
            
        Returns:
            目录统计信息字典
        """
        try:
            image_files = self.scan_directory(directory_path, recursive)
            
            if not image_files:
                return {
                    'directory': directory_path,
                    'total_files': 0,
                    'total_size': 0,
                    'formats': {}
                }
            
            total_size = 0
            formats = {}
            
            for file_path in image_files:
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext not in formats:
                        formats[file_ext] = {'count': 0, 'size': 0}
                    formats[file_ext]['count'] += 1
                    formats[file_ext]['size'] += file_size
                    
                except OSError:
                    continue
            
            return {
                'directory': directory_path,
                'total_files': len(image_files),
                'total_size': total_size,
                'total_size_mb': total_size / 1024 / 1024,
                'formats': formats,
                'average_file_size': total_size / len(image_files) if image_files else 0
            }
            
        except Exception as e:
            logger.error(f"获取目录统计失败: {directory_path}, 错误: {e}")
            return {
                'directory': directory_path,
                'error': str(e)
            }


# 工厂函数
def create_file_handler(config: Optional[Dict] = None) -> FileHandler:
    """创建文件处理器实例
    
    Args:
        config: 配置字典
        
    Returns:
        文件处理器实例
    """
    return FileHandler(config)


def create_progress_tracker(total: int = 0) -> ProgressTracker:
    """创建进度跟踪器实例
    
    Args:
        total: 总任务数
        
    Returns:
        进度跟踪器实例
    """
    return ProgressTracker(total)
