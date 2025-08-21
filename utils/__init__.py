"""
工具函数模块

包含日志、配置加载、验证等工具函数
"""

__version__ = "1.0.0"
__author__ = "OCR Date Recognition Team"

# 工具函数导入 - 延迟导入避免循环依赖
__all__ = [
    'ConfigLoader',
    'setup_logging',
    'get_config',
    'reload_config',
    'get_logger',
    'timing_decorator',
    'PerformanceLogger'
]

def __getattr__(name):
    """延迟导入工具函数"""
    if name in ['ConfigLoader', 'get_config', 'reload_config']:
        from .config_loader import ConfigLoader, get_config, reload_config
        return locals()[name]
    elif name in ['setup_logging', 'get_logger', 'timing_decorator', 'PerformanceLogger']:
        from .logger import setup_logging, get_logger, timing_decorator, PerformanceLogger
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
