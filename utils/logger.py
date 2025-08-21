"""
日志系统模块

提供基于配置的日志初始化和管理功能
"""

import os
import logging
import logging.config
import logging.handlers
import yaml
from typing import Optional, Dict, Any
from pathlib import Path

from .config_loader import get_config


class LoggerSetupError(Exception):
    """日志设置异常"""
    pass


def setup_logging(config_path: Optional[str] = None, 
                 log_level: Optional[str] = None) -> logging.Logger:
    """设置日志系统
    
    Args:
        config_path: 日志配置文件路径，默认为 config/logging.yaml
        log_level: 日志级别，会覆盖配置文件中的设置
        
    Returns:
        配置好的根日志记录器
        
    Raises:
        LoggerSetupError: 日志设置失败
    """
    try:
        # 获取应用配置
        app_config = get_config()
        
        # 确定日志配置文件路径
        if config_path is None:
            config_path = "config/logging.yaml"
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 如果日志配置文件存在，使用文件配置
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                log_config = yaml.safe_load(f)
            
            # 确保日志文件目录存在
            for handler_name, handler_config in log_config.get('handlers', {}).items():
                if 'filename' in handler_config:
                    log_file_path = Path(handler_config['filename'])
                    log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 应用日志配置
            logging.config.dictConfig(log_config)
            
        else:
            # 使用默认配置
            _setup_default_logging(app_config, log_level)
        
        # 覆盖日志级别（如果指定）
        if log_level:
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # 获取根日志记录器
        logger = logging.getLogger()
        logger.info("日志系统初始化完成")
        
        return logger
        
    except Exception as e:
        # 如果日志设置失败，至少设置基本的控制台日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger()
        logger.error(f"日志系统设置失败，使用基本配置: {e}")
        raise LoggerSetupError(f"日志系统设置失败: {e}")


def _setup_default_logging(app_config, log_level: Optional[str] = None) -> None:
    """设置默认日志配置
    
    Args:
        app_config: 应用配置对象
        log_level: 日志级别
    """
    # 从应用配置获取日志设置
    logging_config = app_config.get_section('logging')
    
    # 确定日志级别
    level = log_level or logging_config.get('level', 'INFO')
    level = getattr(logging, level.upper())
    
    # 创建格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    if logging_config.get('console_enabled', True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 文件处理器
    if logging_config.get('file_enabled', True):
        log_file = logging_config.get('file_path', 'logs/app.log')
        
        # 确保日志文件目录存在
        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 解析文件大小
        max_bytes = _parse_file_size(logging_config.get('max_file_size', '10MB'))
        backup_count = logging_config.get('backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 错误文件处理器
    error_log_file = 'logs/error.log'
    error_file_path = Path(error_log_file)
    error_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_file,
        maxBytes=_parse_file_size('10MB'),
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)


def _parse_file_size(size_str: str) -> int:
    """解析文件大小字符串
    
    Args:
        size_str: 文件大小字符串，如 '10MB', '1GB'
        
    Returns:
        字节数
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(float(size_str[:-2]) * 1024)
    elif size_str.endswith('MB'):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith('GB'):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    else:
        # 假设是字节数
        return int(size_str)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


def set_log_level(level: str, logger_name: Optional[str] = None) -> None:
    """设置日志级别
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logger_name: 日志记录器名称，None表示根日志记录器
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))


class PerformanceLogger:
    """性能日志记录器
    
    用于记录函数执行时间和性能指标
    """
    
    def __init__(self, logger_name: str = 'performance'):
        self.logger = logging.getLogger(logger_name)
    
    def log_execution_time(self, func_name: str, execution_time: float, 
                          extra_info: Optional[Dict[str, Any]] = None) -> None:
        """记录函数执行时间
        
        Args:
            func_name: 函数名称
            execution_time: 执行时间（秒）
            extra_info: 额外信息
        """
        message = f"函数 {func_name} 执行时间: {execution_time:.4f}秒"
        if extra_info:
            message += f" | 额外信息: {extra_info}"
        
        self.logger.info(message)
    
    def log_memory_usage(self, func_name: str, memory_usage: float) -> None:
        """记录内存使用情况
        
        Args:
            func_name: 函数名称
            memory_usage: 内存使用量（MB）
        """
        self.logger.info(f"函数 {func_name} 内存使用: {memory_usage:.2f}MB")
    
    def log_batch_performance(self, batch_size: int, total_time: float, 
                            success_count: int, error_count: int) -> None:
        """记录批量处理性能
        
        Args:
            batch_size: 批量大小
            total_time: 总处理时间
            success_count: 成功数量
            error_count: 错误数量
        """
        avg_time = total_time / batch_size if batch_size > 0 else 0
        success_rate = success_count / batch_size if batch_size > 0 else 0
        
        self.logger.info(
            f"批量处理性能 - 总数: {batch_size}, "
            f"总时间: {total_time:.2f}秒, "
            f"平均时间: {avg_time:.4f}秒/个, "
            f"成功率: {success_rate:.2%}, "
            f"错误数: {error_count}"
        )


# 全局性能日志记录器
performance_logger = PerformanceLogger()


def timing_decorator(func):
    """性能计时装饰器
    
    自动记录函数执行时间
    """
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            performance_logger.log_execution_time(func.__name__, execution_time)
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            performance_logger.log_execution_time(
                func.__name__, 
                execution_time, 
                {"error": str(e)}
            )
            raise
    
    return wrapper
