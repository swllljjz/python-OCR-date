"""
配置管理模块

提供YAML配置文件加载、验证和管理功能
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "app": {
        "name": "商品包装生产日期识别系统",
        "version": "1.0.0",
        "debug": False,
        "log_level": "INFO"
    },
    "ocr": {
        "engine": "paddleocr",
        "language": "ch",
        "use_gpu": False,
        "confidence_threshold": 0.8,
        "use_angle_cls": True,
        "det_limit_side_len": 960,
        "det_limit_type": "max"
    },
    "image_processing": {
        "max_width": 1920,
        "max_height": 1080,
        "enhance_contrast": True,
        "contrast_factor": 1.2,
        "denoise": True,
        "denoise_strength": 3,
        "auto_rotate": True,
        "rotation_threshold": 5.0,
        "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
    },
    "date_parsing": {
        "formats": [
            {
                "pattern": r'\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}',
                "description": "YYYY.MM.DD, YYYY-MM-DD, YYYY/MM/DD"
            },
            {
                "pattern": r'\d{8}',
                "description": "YYYYMMDD"
            },
            {
                "pattern": r'\d{4}年\d{1,2}月\d{1,2}日',
                "description": "YYYY年MM月DD日"
            }
        ],
        "year_range": [2020, 2030],
        "strict_validation": True,
        "output_format": "YYYY-MM-DD"
    },
    "performance": {
        "max_workers": 4,
        "batch_size": 10,
        "single_image_timeout": 30,
        "batch_timeout": 300,
        "cache_enabled": True,
        "cache_size": 1000,
        "cache_ttl": 3600,
        "max_memory_usage": 2048,
        "gc_threshold": 100
    },
    "warning": {
        "no_date_found": True,
        "invalid_date": True,
        "low_confidence": True,
        "processing_error": True,
        "low_confidence_threshold": 0.6
    },
    "logging": {
        "level": "INFO",
        "file_enabled": True,
        "file_path": "logs/app.log",
        "max_file_size": "10MB",
        "backup_count": 5,
        "console_enabled": True
    }
}


class ConfigurationError(Exception):
    """配置异常"""
    pass


class ConfigLoader:
    """配置加载器类
    
    负责加载、验证和管理项目配置
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置加载器
        
        Args:
            config_path: 配置文件路径，默认为 config/settings.yaml
        """
        self.config_path = config_path or "config/settings.yaml"
        self._config = None
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            # 首先使用默认配置
            self._config = DEFAULT_CONFIG.copy()
            
            # 如果配置文件存在，则加载并合并
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        self._merge_config(self._config, file_config)
                        logger.info(f"配置文件加载成功: {self.config_path}")
            else:
                logger.warning(f"配置文件不存在，使用默认配置: {self.config_path}")
            
            # 加载环境变量
            self._load_env_variables()
            
            # 验证配置
            self._validate_config()
            
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise ConfigurationError(f"配置加载失败: {e}")
    
    def _merge_config(self, base_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """递归合并配置字典
        
        Args:
            base_config: 基础配置字典
            new_config: 新配置字典
        """
        for key, value in new_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._merge_config(base_config[key], value)
            else:
                base_config[key] = value
    
    def _load_env_variables(self) -> None:
        """加载环境变量覆盖配置"""
        env_mappings = {
            'OCR_USE_GPU': ('ocr', 'use_gpu'),
            'OCR_CONFIDENCE_THRESHOLD': ('ocr', 'confidence_threshold'),
            'MAX_WORKERS': ('performance', 'max_workers'),
            'LOG_LEVEL': ('logging', 'level'),
            'DEBUG': ('app', 'debug')
        }
        
        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # 尝试转换数据类型
                    if env_var in ['OCR_USE_GPU', 'DEBUG']:
                        env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif env_var in ['OCR_CONFIDENCE_THRESHOLD']:
                        env_value = float(env_value)
                    elif env_var in ['MAX_WORKERS']:
                        env_value = int(env_value)
                    
                    self._config[section][key] = env_value
                    logger.info(f"环境变量覆盖配置: {env_var} = {env_value}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"环境变量 {env_var} 值无效: {env_value}, 错误: {e}")
    
    def _validate_config(self) -> None:
        """验证配置有效性"""
        # 验证OCR配置
        ocr_config = self._config.get('ocr', {})
        if ocr_config.get('confidence_threshold', 0) < 0 or ocr_config.get('confidence_threshold', 0) > 1:
            raise ConfigurationError("OCR置信度阈值必须在0-1之间")
        
        # 验证性能配置
        perf_config = self._config.get('performance', {})
        if perf_config.get('max_workers', 1) < 1:
            raise ConfigurationError("最大工作线程数必须大于0")
        
        # 验证日期解析配置
        date_config = self._config.get('date_parsing', {})
        year_range = date_config.get('year_range', [2020, 2030])
        if len(year_range) != 2 or year_range[0] >= year_range[1]:
            raise ConfigurationError("年份范围配置无效")
        
        logger.info("配置验证通过")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键 (如: 'ocr.confidence_threshold')
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置段
        
        Args:
            section: 配置段名称
            
        Returns:
            配置段字典
        """
        return self._config.get(section, {})
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        # 导航到最后一级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        logger.info(f"配置已更新: {key} = {value}")
    
    def reload(self) -> None:
        """重新加载配置文件"""
        logger.info("重新加载配置文件")
        self._load_config()
    
    def save(self, output_path: Optional[str] = None) -> None:
        """保存当前配置到文件
        
        Args:
            output_path: 输出文件路径，默认为原配置文件路径
        """
        output_path = output_path or self.config_path
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"配置已保存到: {output_path}")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise ConfigurationError(f"配置保存失败: {e}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return self._config.copy()


# 全局配置实例
_global_config = None


def get_config() -> ConfigLoader:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader()
    return _global_config


def reload_config() -> None:
    """重新加载全局配置"""
    global _global_config
    if _global_config is not None:
        _global_config.reload()
    else:
        _global_config = ConfigLoader()
