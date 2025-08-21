"""
核心数据模型

定义项目中使用的所有数据结构和模型
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


@dataclass
class TextResult:
    """OCR文本识别结果"""
    
    text: str                         # 识别的文本
    confidence: float                 # 置信度 (0.0-1.0)
    bbox: List[List[int]]            # 文本边界框坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    
    def get_center_point(self) -> Tuple[int, int]:
        """获取文本中心点坐标
        
        Returns:
            文本中心点坐标 (x, y)
        """
        if not self.bbox or len(self.bbox) < 4:
            return (0, 0)
        
        # 计算边界框的中心点
        x_coords = [point[0] for point in self.bbox]
        y_coords = [point[1] for point in self.bbox]
        
        center_x = sum(x_coords) // len(x_coords)
        center_y = sum(y_coords) // len(y_coords)
        
        return (center_x, center_y)
    
    def get_bbox_area(self) -> float:
        """获取边界框面积
        
        Returns:
            边界框面积
        """
        if not self.bbox or len(self.bbox) < 4:
            return 0.0
        
        # 使用鞋带公式计算多边形面积
        x_coords = [point[0] for point in self.bbox]
        y_coords = [point[1] for point in self.bbox]
        
        n = len(x_coords)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += x_coords[i] * y_coords[j]
            area -= x_coords[j] * y_coords[i]
        
        return abs(area) / 2.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


@dataclass
class DateInfo:
    """日期信息模型"""
    
    original_text: str               # 原始文本
    parsed_date: str                 # 解析后的标准日期格式 (YYYY-MM-DD)
    confidence: float                # 日期解析置信度
    format_type: str                 # 日期格式类型
    position: Tuple[int, int]        # 在图像中的位置
    
    def is_valid(self) -> bool:
        """检查日期是否有效
        
        Returns:
            日期是否有效
        """
        try:
            datetime.strptime(self.parsed_date, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


@dataclass
class RecognitionResult:
    """单张图片识别结果"""
    
    image_path: str                    # 图片路径
    success: bool                      # 是否识别成功
    dates_found: List[str]            # 识别到的日期列表 (标准格式)
    confidence: float                  # 整体置信度 (0.0-1.0)
    processing_time: float            # 处理时间(秒)
    warning_message: Optional[str]     # 警告信息
    raw_text: List[str]               # OCR原始文本结果
    image_size: Tuple[int, int]       # 图片尺寸 (width, height)
    date_details: List[DateInfo]      # 详细日期信息
    ocr_results: List[TextResult]     # OCR详细结果
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保列表不为None
        if self.dates_found is None:
            self.dates_found = []
        if self.raw_text is None:
            self.raw_text = []
        if self.date_details is None:
            self.date_details = []
        if self.ocr_results is None:
            self.ocr_results = []
    
    def is_valid_date(self) -> bool:
        """检查是否包含有效日期
        
        Returns:
            是否包含有效日期
        """
        return self.success and len(self.dates_found) > 0
    
    def get_best_date(self) -> Optional[str]:
        """获取置信度最高的日期
        
        Returns:
            置信度最高的日期，如果没有则返回None
        """
        if not self.date_details:
            return self.dates_found[0] if self.dates_found else None
        
        # 按置信度排序，返回最高的
        best_date = max(self.date_details, key=lambda d: d.confidence)
        return best_date.parsed_date
    
    def get_warning_level(self) -> str:
        """获取警告级别
        
        Returns:
            警告级别: 'none', 'low', 'medium', 'high'
        """
        if not self.success:
            return 'high'
        elif not self.dates_found:
            return 'high'
        elif self.confidence < 0.6:
            return 'medium'
        elif self.confidence < 0.8:
            return 'low'
        else:
            return 'none'
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            字典格式的结果
        """
        result_dict = asdict(self)
        
        # 转换日期详情
        result_dict['date_details'] = [detail.to_dict() for detail in self.date_details]
        
        # 转换OCR结果
        result_dict['ocr_results'] = [ocr.to_dict() for ocr in self.ocr_results]
        
        # 添加额外信息
        result_dict['warning_level'] = self.get_warning_level()
        result_dict['best_date'] = self.get_best_date()
        
        return result_dict
    
    def to_json(self) -> str:
        """转换为JSON字符串
        
        Returns:
            JSON格式的结果
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class BatchResult:
    """批量处理结果"""
    
    folder_path: str                   # 处理的文件夹路径
    total_files: int                   # 总文件数
    total_processed: int               # 已处理文件数
    successful_recognitions: int       # 成功识别数
    failed_recognitions: int           # 失败识别数
    processing_time: float             # 总处理时间(秒)
    results: List[RecognitionResult]   # 详细结果列表
    start_time: Optional[str]          # 开始时间
    end_time: Optional[str]            # 结束时间
    
    def __post_init__(self):
        """初始化后处理"""
        if self.results is None:
            self.results = []
        
        # 设置时间戳
        if self.start_time is None:
            self.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self.end_time is None:
            self.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def success_rate(self) -> float:
        """成功率
        
        Returns:
            成功率 (0.0-1.0)
        """
        if self.total_processed == 0:
            return 0.0
        return self.successful_recognitions / self.total_processed
    
    @property
    def average_processing_time(self) -> float:
        """平均处理时间
        
        Returns:
            平均处理时间(秒)
        """
        if self.total_processed == 0:
            return 0.0
        return self.processing_time / self.total_processed
    
    def get_failed_results(self) -> List[RecognitionResult]:
        """获取失败的识别结果
        
        Returns:
            失败的识别结果列表
        """
        return [result for result in self.results if not result.success]
    
    def get_successful_results(self) -> List[RecognitionResult]:
        """获取成功的识别结果
        
        Returns:
            成功的识别结果列表
        """
        return [result for result in self.results if result.success]
    
    def get_warning_results(self) -> List[RecognitionResult]:
        """获取有警告的识别结果
        
        Returns:
            有警告的识别结果列表
        """
        return [result for result in self.results 
                if result.get_warning_level() in ['medium', 'high']]
    
    def generate_report(self) -> str:
        """生成处理报告
        
        Returns:
            处理报告字符串
        """
        report_lines = [
            "=" * 60,
            "批量处理报告",
            "=" * 60,
            f"处理文件夹: {self.folder_path}",
            f"开始时间: {self.start_time}",
            f"结束时间: {self.end_time}",
            f"总处理时间: {self.processing_time:.2f}秒",
            "",
            "处理统计:",
            f"  总文件数: {self.total_files}",
            f"  已处理数: {self.total_processed}",
            f"  成功识别: {self.successful_recognitions}",
            f"  失败识别: {self.failed_recognitions}",
            f"  成功率: {self.success_rate:.2%}",
            f"  平均处理时间: {self.average_processing_time:.4f}秒/张",
            "",
        ]
        
        # 添加警告统计
        warning_results = self.get_warning_results()
        if warning_results:
            report_lines.extend([
                "警告统计:",
                f"  有警告的文件数: {len(warning_results)}",
                ""
            ])
        
        # 添加失败详情
        failed_results = self.get_failed_results()
        if failed_results:
            report_lines.extend([
                "失败详情:",
            ])
            for result in failed_results[:10]:  # 最多显示10个失败案例
                report_lines.append(f"  {result.image_path}: {result.warning_message}")
            
            if len(failed_results) > 10:
                report_lines.append(f"  ... 还有 {len(failed_results) - 10} 个失败案例")
            report_lines.append("")
        
        # 添加成功案例统计
        successful_results = self.get_successful_results()
        if successful_results:
            date_counts = {}
            for result in successful_results:
                for date in result.dates_found:
                    date_counts[date] = date_counts.get(date, 0) + 1
            
            if date_counts:
                report_lines.extend([
                    "识别到的日期统计:",
                ])
                for date, count in sorted(date_counts.items()):
                    report_lines.append(f"  {date}: {count}次")
                report_lines.append("")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式
        
        Returns:
            字典格式的结果
        """
        result_dict = asdict(self)
        
        # 转换结果列表
        result_dict['results'] = [result.to_dict() for result in self.results]
        
        # 添加计算属性
        result_dict['success_rate'] = self.success_rate
        result_dict['average_processing_time'] = self.average_processing_time
        
        return result_dict
    
    def to_json(self) -> str:
        """转换为JSON字符串
        
        Returns:
            JSON格式的结果
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def save_report(self, output_path: str) -> None:
        """保存报告到文件
        
        Args:
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())


# 工厂函数
def create_recognition_result(image_path: str, 
                            success: bool = False,
                            processing_time: float = 0.0,
                            image_size: Tuple[int, int] = (0, 0)) -> RecognitionResult:
    """创建识别结果对象
    
    Args:
        image_path: 图片路径
        success: 是否成功
        processing_time: 处理时间
        image_size: 图片尺寸
        
    Returns:
        识别结果对象
    """
    return RecognitionResult(
        image_path=image_path,
        success=success,
        dates_found=[],
        confidence=0.0,
        processing_time=processing_time,
        warning_message=None,
        raw_text=[],
        image_size=image_size,
        date_details=[],
        ocr_results=[]
    )


def create_batch_result(folder_path: str) -> BatchResult:
    """创建批量处理结果对象
    
    Args:
        folder_path: 文件夹路径
        
    Returns:
        批量处理结果对象
    """
    return BatchResult(
        folder_path=folder_path,
        total_files=0,
        total_processed=0,
        successful_recognitions=0,
        failed_recognitions=0,
        processing_time=0.0,
        results=[],
        start_time=None,
        end_time=None
    )
