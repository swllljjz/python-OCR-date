"""
日期解析模块

提供从OCR文本中解析和验证日期的功能
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from dataclasses import dataclass

from .models import TextResult, DateInfo
from utils.config_loader import get_config
from utils.validators import validate_date_string

logger = logging.getLogger(__name__)


class DateParsingError(Exception):
    """日期解析异常"""
    pass


@dataclass
class DatePattern:
    """日期模式定义"""
    pattern: str           # 正则表达式模式
    description: str       # 模式描述
    format_type: str       # 格式类型
    weight: float         # 权重（用于置信度计算）
    parser_func: str      # 解析函数名


class DateParser:
    """日期解析和验证类
    
    负责从OCR文本结果中识别、解析和验证日期信息
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """初始化日期解析器
        
        Args:
            config: 配置字典，如果为None则使用全局配置
        """
        if config is None:
            app_config = get_config()
            self.config = app_config.get_section('date_parsing')
        else:
            self.config = config.get('date_parsing', {})
        
        # 配置参数
        self.year_range = tuple(self.config.get('year_range', [2020, 2030]))
        self.strict_validation = self.config.get('strict_validation', True)
        self.output_format = self.config.get('output_format', 'YYYY-MM-DD')
        
        # 初始化日期模式
        self.date_patterns = self._initialize_date_patterns()
        
        logger.info("日期解析器初始化完成")
    
    def _initialize_date_patterns(self) -> List[DatePattern]:
        """初始化日期模式列表"""
        patterns = []
        
        # 从配置获取格式定义
        format_configs = self.config.get('formats', [])
        
        # 默认模式（如果配置为空）
        if not format_configs:
            format_configs = [
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
            ]
        
        # 创建DatePattern对象
        for i, fmt_config in enumerate(format_configs):
            pattern = DatePattern(
                pattern=fmt_config['pattern'],
                description=fmt_config.get('description', f'Pattern {i+1}'),
                format_type=self._get_format_type(fmt_config['pattern']),
                weight=fmt_config.get('weight', 1.0),
                parser_func=self._get_parser_function(fmt_config['pattern'])
            )
            patterns.append(pattern)
        
        logger.debug(f"初始化了 {len(patterns)} 个日期模式")
        return patterns
    
    def _get_format_type(self, pattern: str) -> str:
        """根据模式获取格式类型"""
        if '年' in pattern and '月' in pattern and '日' in pattern:
            return 'CHINESE'
        elif r'\d{8}' in pattern:
            return 'YYYYMMDD'
        elif r'[.\-/]' in pattern:
            return 'SEPARATED'
        else:
            return 'UNKNOWN'

    def _get_parser_function(self, pattern: str) -> str:
        """根据模式获取解析函数名"""
        if '年' in pattern:
            return '_parse_chinese_date'
        elif r'\d{8}' in pattern:
            return '_parse_compact_date'
        elif r'[.\-/]' in pattern:
            return '_parse_separated_date'
        else:
            return '_parse_generic_date'
    
    def parse_dates_from_text(self, text_results: List[TextResult]) -> List[DateInfo]:
        """从文本结果中解析日期
        
        Args:
            text_results: OCR文本结果列表
            
        Returns:
            解析出的日期信息列表
        """
        date_infos = []
        
        try:
            for text_result in text_results:
                # 从单个文本中解析日期
                dates = self._parse_single_text(text_result)
                date_infos.extend(dates)
            
            # 去重和排序
            date_infos = self._deduplicate_dates(date_infos)
            date_infos.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"从 {len(text_results)} 个文本中解析出 {len(date_infos)} 个日期")
            return date_infos
            
        except Exception as e:
            logger.error(f"日期解析失败: {e}")
            raise DateParsingError(f"日期解析失败: {e}")
    
    def _parse_single_text(self, text_result: TextResult) -> List[DateInfo]:
        """从单个文本中解析日期
        
        Args:
            text_result: 单个文本结果
            
        Returns:
            解析出的日期信息列表
        """
        date_infos = []
        text = text_result.text
        
        for pattern in self.date_patterns:
            try:
                # 使用正则表达式查找匹配
                matches = re.finditer(pattern.pattern, text)
                
                for match in matches:
                    matched_text = match.group()
                    
                    # 解析日期
                    parsed_date = self._parse_date_by_pattern(matched_text, pattern)
                    
                    if parsed_date:
                        # 计算置信度
                        confidence = self._calculate_confidence(
                            text_result.confidence, pattern.weight, matched_text
                        )
                        
                        # 获取位置
                        position = text_result.get_center_point()
                        
                        date_info = DateInfo(
                            original_text=matched_text,
                            parsed_date=parsed_date,
                            confidence=confidence,
                            format_type=pattern.format_type,
                            position=position
                        )
                        
                        date_infos.append(date_info)
                        logger.debug(f"解析日期: {matched_text} -> {parsed_date}")
                        
            except Exception as e:
                logger.warning(f"模式 {pattern.pattern} 解析失败: {e}")
                continue
        
        return date_infos
    
    def _parse_date_by_pattern(self, text: str, pattern: DatePattern) -> Optional[str]:
        """根据模式解析日期
        
        Args:
            text: 匹配的文本
            pattern: 日期模式
            
        Returns:
            标准化的日期字符串，失败返回None
        """
        try:
            # 根据解析函数名调用相应的解析方法
            parser_func = getattr(self, pattern.parser_func, self._parse_generic_date)
            return parser_func(text)
            
        except Exception as e:
            logger.debug(f"日期解析失败: {text}, 错误: {e}")
            return None
    
    def _parse_chinese_date(self, text: str) -> Optional[str]:
        """解析中文日期格式 (YYYY年MM月DD日)"""
        try:
            # 提取年月日
            year_match = re.search(r'(\d{4})年', text)
            month_match = re.search(r'(\d{1,2})月', text)
            day_match = re.search(r'(\d{1,2})日', text)
            
            if year_match and month_match and day_match:
                year = int(year_match.group(1))
                month = int(month_match.group(1))
                day = int(day_match.group(1))
                
                return self._format_date(year, month, day)
            
            return None
            
        except Exception:
            return None
    
    def _parse_compact_date(self, text: str) -> Optional[str]:
        """解析紧凑日期格式 (YYYYMMDD)"""
        try:
            if len(text) == 8 and text.isdigit():
                year = int(text[:4])
                month = int(text[4:6])
                day = int(text[6:8])
                
                return self._format_date(year, month, day)
            
            return None
            
        except Exception:
            return None
    
    def _parse_separated_date(self, text: str) -> Optional[str]:
        """解析分隔符日期格式 (YYYY.MM.DD, YYYY-MM-DD, YYYY/MM/DD)"""
        try:
            # 使用多种分隔符进行分割
            parts = re.split(r'[.\-/]', text)
            
            if len(parts) == 3:
                # 判断日期格式 (YYYY-MM-DD 或 DD-MM-YYYY)
                if len(parts[0]) == 4:  # YYYY-MM-DD
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                elif len(parts[2]) == 4:  # DD-MM-YYYY
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    return None
                
                return self._format_date(year, month, day)
            
            return None
            
        except Exception:
            return None
    
    def _parse_generic_date(self, text: str) -> Optional[str]:
        """通用日期解析"""
        try:
            # 尝试多种常见格式
            formats = [
                '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
                '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
                '%Y%m%d'
            ]
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(text, fmt)
                    return parsed.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _format_date(self, year: int, month: int, day: int) -> Optional[str]:
        """格式化日期
        
        Args:
            year: 年
            month: 月
            day: 日
            
        Returns:
            标准化的日期字符串
        """
        try:
            # 验证日期有效性
            date_obj = date(year, month, day)
            
            # 检查年份范围
            if not (self.year_range[0] <= year <= self.year_range[1]):
                if self.strict_validation:
                    return None
                else:
                    logger.warning(f"日期年份超出范围: {year}")
            
            return date_obj.strftime('%Y-%m-%d')
            
        except ValueError:
            return None
    
    def _calculate_confidence(self, ocr_confidence: float, 
                            pattern_weight: float, text: str) -> float:
        """计算日期解析置信度
        
        Args:
            ocr_confidence: OCR识别置信度
            pattern_weight: 模式权重
            text: 匹配的文本
            
        Returns:
            综合置信度
        """
        # 基础置信度 = OCR置信度 * 模式权重
        base_confidence = ocr_confidence * pattern_weight
        
        # 文本质量加权
        text_quality = self._assess_text_quality(text)
        
        # 综合置信度
        final_confidence = base_confidence * text_quality
        
        return min(final_confidence, 1.0)
    
    def _assess_text_quality(self, text: str) -> float:
        """评估文本质量
        
        Args:
            text: 文本内容
            
        Returns:
            质量评分 (0.0-1.0)
        """
        quality = 1.0
        
        # 长度检查
        if len(text) < 6:  # 最短日期格式
            quality *= 0.8
        elif len(text) > 15:  # 过长可能包含其他内容
            quality *= 0.9
        
        # 数字比例检查
        digit_ratio = sum(c.isdigit() for c in text) / len(text)
        if digit_ratio < 0.5:
            quality *= 0.8
        
        # 特殊字符检查
        if any(c in text for c in '!@#$%^&*()'):
            quality *= 0.7
        
        return quality
    
    def _deduplicate_dates(self, date_infos: List[DateInfo]) -> List[DateInfo]:
        """去除重复日期
        
        Args:
            date_infos: 日期信息列表
            
        Returns:
            去重后的日期信息列表
        """
        seen_dates = {}
        unique_dates = []
        
        for date_info in date_infos:
            date_key = date_info.parsed_date
            
            if date_key not in seen_dates:
                seen_dates[date_key] = date_info
                unique_dates.append(date_info)
            else:
                # 保留置信度更高的
                if date_info.confidence > seen_dates[date_key].confidence:
                    # 替换原有的
                    for i, existing in enumerate(unique_dates):
                        if existing.parsed_date == date_key:
                            unique_dates[i] = date_info
                            break
                    seen_dates[date_key] = date_info
        
        return unique_dates
    
    def validate_date(self, date_str: str) -> bool:
        """验证日期有效性
        
        Args:
            date_str: 日期字符串
            
        Returns:
            是否为有效日期
        """
        try:
            validate_date_string(date_str, self.year_range)
            return True
        except Exception:
            return False
    
    def standardize_format(self, date_str: str) -> str:
        """标准化日期格式
        
        Args:
            date_str: 原始日期字符串
            
        Returns:
            标准化后的日期字符串 (YYYY-MM-DD)
        """
        try:
            # 如果已经是标准格式，直接返回
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                return date_str
            
            # 尝试解析并重新格式化
            for pattern in self.date_patterns:
                if re.match(pattern.pattern, date_str):
                    parsed = self._parse_date_by_pattern(date_str, pattern)
                    if parsed:
                        return parsed
            
            # 如果无法解析，返回原字符串
            return date_str
            
        except Exception as e:
            logger.warning(f"日期格式标准化失败: {date_str}, 错误: {e}")
            return date_str
    
    def get_parser_info(self) -> Dict[str, Any]:
        """获取解析器信息
        
        Returns:
            解析器信息字典
        """
        return {
            'year_range': self.year_range,
            'strict_validation': self.strict_validation,
            'output_format': self.output_format,
            'pattern_count': len(self.date_patterns),
            'patterns': [
                {
                    'pattern': p.pattern,
                    'description': p.description,
                    'format_type': p.format_type,
                    'weight': p.weight
                }
                for p in self.date_patterns
            ]
        }


# 工厂函数
def create_date_parser(config: Optional[Dict] = None) -> DateParser:
    """创建日期解析器实例
    
    Args:
        config: 配置字典
        
    Returns:
        日期解析器实例
    """
    return DateParser(config)
