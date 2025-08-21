"""
验证工具模块

提供各种数据验证和格式检查功能
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union
from datetime import datetime, date


class ValidationError(Exception):
    """验证异常"""
    pass


def validate_image_file(file_path: str, 
                       supported_formats: Optional[List[str]] = None) -> bool:
    """验证图像文件
    
    Args:
        file_path: 文件路径
        supported_formats: 支持的文件格式列表
        
    Returns:
        是否为有效的图像文件
        
    Raises:
        ValidationError: 验证失败
    """
    if supported_formats is None:
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise ValidationError(f"文件不存在: {file_path}")
    
    # 检查是否为文件
    if not os.path.isfile(file_path):
        raise ValidationError(f"路径不是文件: {file_path}")
    
    # 检查文件扩展名
    file_ext = Path(file_path).suffix.lower()
    if file_ext not in supported_formats:
        raise ValidationError(f"不支持的文件格式: {file_ext}, 支持的格式: {supported_formats}")
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise ValidationError(f"文件为空: {file_path}")
    
    # 检查文件大小限制 (100MB)
    max_size = 100 * 1024 * 1024  # 100MB
    if file_size > max_size:
        raise ValidationError(f"文件过大: {file_size / 1024 / 1024:.2f}MB > 100MB")
    
    return True


def validate_directory(dir_path: str, 
                      must_exist: bool = True,
                      must_be_readable: bool = True) -> bool:
    """验证目录
    
    Args:
        dir_path: 目录路径
        must_exist: 目录必须存在
        must_be_readable: 目录必须可读
        
    Returns:
        是否为有效目录
        
    Raises:
        ValidationError: 验证失败
    """
    if must_exist and not os.path.exists(dir_path):
        raise ValidationError(f"目录不存在: {dir_path}")
    
    if os.path.exists(dir_path):
        if not os.path.isdir(dir_path):
            raise ValidationError(f"路径不是目录: {dir_path}")
        
        if must_be_readable and not os.access(dir_path, os.R_OK):
            raise ValidationError(f"目录不可读: {dir_path}")
    
    return True


def validate_date_string(date_str: str, 
                        year_range: Optional[Tuple[int, int]] = None) -> bool:
    """验证日期字符串
    
    Args:
        date_str: 日期字符串
        year_range: 有效年份范围 (min_year, max_year)
        
    Returns:
        是否为有效日期
        
    Raises:
        ValidationError: 验证失败
    """
    if not date_str or not isinstance(date_str, str):
        raise ValidationError("日期字符串不能为空")
    
    # 尝试解析标准格式日期
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError(f"日期格式无效: {date_str}, 期望格式: YYYY-MM-DD")
    
    # 检查年份范围
    if year_range:
        min_year, max_year = year_range
        if parsed_date.year < min_year or parsed_date.year > max_year:
            raise ValidationError(f"日期年份超出范围: {parsed_date.year}, 有效范围: {min_year}-{max_year}")
    
    # 检查日期合理性
    today = date.today()
    if parsed_date > today:
        # 允许未来1年内的日期（考虑保质期等情况）
        max_future_date = date(today.year + 1, today.month, today.day)
        if parsed_date > max_future_date:
            raise ValidationError(f"日期过于未来: {date_str}")
    
    # 检查日期不能太久远
    min_date = date(1900, 1, 1)
    if parsed_date < min_date:
        raise ValidationError(f"日期过于久远: {date_str}")
    
    return True


def validate_confidence(confidence: float) -> bool:
    """验证置信度值
    
    Args:
        confidence: 置信度值
        
    Returns:
        是否为有效置信度
        
    Raises:
        ValidationError: 验证失败
    """
    if not isinstance(confidence, (int, float)):
        raise ValidationError(f"置信度必须是数字: {type(confidence)}")
    
    if confidence < 0.0 or confidence > 1.0:
        raise ValidationError(f"置信度必须在0-1之间: {confidence}")
    
    return True


def validate_image_size(width: int, height: int, 
                       max_width: int = 10000, 
                       max_height: int = 10000) -> bool:
    """验证图像尺寸
    
    Args:
        width: 图像宽度
        height: 图像高度
        max_width: 最大宽度
        max_height: 最大高度
        
    Returns:
        是否为有效尺寸
        
    Raises:
        ValidationError: 验证失败
    """
    if not isinstance(width, int) or not isinstance(height, int):
        raise ValidationError("图像尺寸必须是整数")
    
    if width <= 0 or height <= 0:
        raise ValidationError(f"图像尺寸必须大于0: {width}x{height}")
    
    if width > max_width or height > max_height:
        raise ValidationError(f"图像尺寸过大: {width}x{height}, 最大: {max_width}x{max_height}")
    
    return True


def validate_bbox(bbox: List[List[int]]) -> bool:
    """验证边界框坐标
    
    Args:
        bbox: 边界框坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        
    Returns:
        是否为有效边界框
        
    Raises:
        ValidationError: 验证失败
    """
    if not isinstance(bbox, list):
        raise ValidationError("边界框必须是列表")
    
    if len(bbox) != 4:
        raise ValidationError(f"边界框必须包含4个点: {len(bbox)}")
    
    for i, point in enumerate(bbox):
        if not isinstance(point, list) or len(point) != 2:
            raise ValidationError(f"边界框点{i}格式错误: {point}")
        
        if not all(isinstance(coord, (int, float)) for coord in point):
            raise ValidationError(f"边界框点{i}坐标必须是数字: {point}")
        
        if any(coord < 0 for coord in point):
            raise ValidationError(f"边界框点{i}坐标不能为负数: {point}")
    
    return True


def validate_date_format_pattern(pattern: str) -> bool:
    """验证日期格式正则表达式
    
    Args:
        pattern: 正则表达式模式
        
    Returns:
        是否为有效模式
        
    Raises:
        ValidationError: 验证失败
    """
    if not pattern or not isinstance(pattern, str):
        raise ValidationError("日期格式模式不能为空")
    
    try:
        re.compile(pattern)
    except re.error as e:
        raise ValidationError(f"日期格式模式无效: {pattern}, 错误: {e}")
    
    return True


def validate_config_section(config: dict, required_keys: List[str]) -> bool:
    """验证配置段
    
    Args:
        config: 配置字典
        required_keys: 必需的键列表
        
    Returns:
        是否为有效配置
        
    Raises:
        ValidationError: 验证失败
    """
    if not isinstance(config, dict):
        raise ValidationError("配置必须是字典")
    
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValidationError(f"配置缺少必需的键: {missing_keys}")
    
    return True


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除或替换非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_len = 255 - len(ext)
        filename = name[:max_name_len] + ext
    
    return filename


def is_valid_image_extension(file_path: str, 
                           supported_formats: Optional[List[str]] = None) -> bool:
    """检查文件扩展名是否为支持的图像格式
    
    Args:
        file_path: 文件路径
        supported_formats: 支持的格式列表
        
    Returns:
        是否为支持的图像格式
    """
    if supported_formats is None:
        supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    file_ext = Path(file_path).suffix.lower()
    return file_ext in supported_formats


def normalize_path(path: str) -> str:
    """标准化路径
    
    Args:
        path: 原始路径
        
    Returns:
        标准化后的路径
    """
    # 转换为绝对路径
    path = os.path.abspath(path)
    
    # 标准化路径分隔符
    path = os.path.normpath(path)
    
    return path


def get_safe_filename(base_name: str, extension: str, output_dir: str) -> str:
    """生成安全的文件名，避免覆盖现有文件
    
    Args:
        base_name: 基础文件名
        extension: 文件扩展名
        output_dir: 输出目录
        
    Returns:
        安全的文件名
    """
    base_name = sanitize_filename(base_name)
    extension = extension.lower()
    
    if not extension.startswith('.'):
        extension = '.' + extension
    
    counter = 0
    while True:
        if counter == 0:
            filename = f"{base_name}{extension}"
        else:
            filename = f"{base_name}_{counter}{extension}"
        
        full_path = os.path.join(output_dir, filename)
        if not os.path.exists(full_path):
            return filename
        
        counter += 1
        if counter > 1000:  # 防止无限循环
            raise ValidationError("无法生成唯一文件名")
