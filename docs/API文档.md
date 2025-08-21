# API文档

## 1. 核心API概览

### 1.1 主要类和接口
- `DateRecognizer`: 主要的日期识别接口
- `OCREngine`: OCR识别引擎
- `DateParser`: 日期解析器
- `ImageProcessor`: 图像处理器
- `BatchProcessor`: 批量处理器

## 2. DateRecognizer 类

### 2.1 类定义
```python
class DateRecognizer:
    """统一的日期识别接口类
    
    提供单张图片识别、批量识别和文件夹识别功能
    """
```

### 2.2 初始化方法
```python
def __init__(self, config: Optional[Dict] = None) -> None:
    """初始化日期识别器
    
    Args:
        config (Optional[Dict]): 配置字典，如果为None则使用默认配置
        
    Example:
        >>> recognizer = DateRecognizer()
        >>> # 或使用自定义配置
        >>> config = {"ocr": {"confidence_threshold": 0.9}}
        >>> recognizer = DateRecognizer(config)
    """
```

### 2.3 单张图片识别
```python
def recognize_single(self, image_path: str) -> RecognitionResult:
    """识别单张图片中的日期
    
    Args:
        image_path (str): 图片文件路径
        
    Returns:
        RecognitionResult: 识别结果对象
        
    Raises:
        FileNotFoundError: 图片文件不存在
        ValueError: 图片格式不支持
        OCRException: OCR识别过程中的错误
        
    Example:
        >>> result = recognizer.recognize_single("test.jpg")
        >>> if result.success:
        ...     print(f"识别到日期: {result.dates_found}")
        ... else:
        ...     print(f"识别失败: {result.warning_message}")
    """
```

### 2.4 批量识别
```python
def recognize_batch(self, image_paths: List[str], 
                   max_workers: int = 4) -> List[RecognitionResult]:
    """批量识别多张图片
    
    Args:
        image_paths (List[str]): 图片文件路径列表
        max_workers (int): 最大并行工作线程数，默认为4
        
    Returns:
        List[RecognitionResult]: 识别结果列表
        
    Example:
        >>> paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        >>> results = recognizer.recognize_batch(paths)
        >>> success_count = sum(1 for r in results if r.success)
        >>> print(f"成功识别 {success_count}/{len(results)} 张图片")
    """
```

### 2.5 文件夹识别
```python
def recognize_folder(self, folder_path: str, 
                    recursive: bool = True,
                    file_extensions: List[str] = None) -> BatchResult:
    """识别文件夹中的所有图片
    
    Args:
        folder_path (str): 文件夹路径
        recursive (bool): 是否递归扫描子文件夹，默认为True
        file_extensions (List[str]): 支持的文件扩展名，默认为['.jpg', '.jpeg', '.png', '.bmp']
        
    Returns:
        BatchResult: 批量处理结果对象
        
    Example:
        >>> result = recognizer.recognize_folder("./images")
        >>> print(f"处理完成: {result.total_processed} 张图片")
        >>> print(f"成功率: {result.success_rate:.2%}")
    """
```

## 3. 数据模型

### 3.1 RecognitionResult
```python
@dataclass
class RecognitionResult:
    """单张图片识别结果"""
    
    image_path: str                    # 图片路径
    success: bool                      # 是否识别成功
    dates_found: List[str]            # 识别到的日期列表
    confidence: float                  # 置信度 (0.0-1.0)
    processing_time: float            # 处理时间(秒)
    warning_message: Optional[str]     # 警告信息
    raw_text: List[str]               # OCR原始文本结果
    image_size: Tuple[int, int]       # 图片尺寸 (width, height)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        
    def is_valid_date(self) -> bool:
        """检查是否包含有效日期"""
```

### 3.2 BatchResult
```python
@dataclass
class BatchResult:
    """批量处理结果"""
    
    folder_path: str                   # 处理的文件夹路径
    total_files: int                   # 总文件数
    total_processed: int               # 已处理文件数
    successful_recognitions: int       # 成功识别数
    failed_recognitions: int           # 失败识别数
    processing_time: float             # 总处理时间
    results: List[RecognitionResult]   # 详细结果列表
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        
    def get_failed_results(self) -> List[RecognitionResult]:
        """获取失败的识别结果"""
        
    def generate_report(self) -> str:
        """生成处理报告"""
```

### 3.3 TextResult
```python
@dataclass
class TextResult:
    """OCR文本识别结果"""
    
    text: str                         # 识别的文本
    confidence: float                 # 置信度
    bbox: List[List[int]]            # 文本边界框坐标
    
    def get_center_point(self) -> Tuple[int, int]:
        """获取文本中心点坐标"""
```

## 4. OCREngine 类

### 4.1 类定义
```python
class OCREngine:
    """OCR识别引擎封装类"""
    
    def __init__(self, config: Dict):
        """初始化OCR引擎
        
        Args:
            config (Dict): OCR配置参数
        """
```

### 4.2 主要方法
```python
def recognize_text(self, image: np.ndarray) -> List[TextResult]:
    """识别图像中的文本
    
    Args:
        image (np.ndarray): 输入图像数组
        
    Returns:
        List[TextResult]: 文本识别结果列表
    """

def detect_orientation(self, image: np.ndarray) -> float:
    """检测文本方向
    
    Args:
        image (np.ndarray): 输入图像
        
    Returns:
        float: 旋转角度(度)
    """
```

## 5. DateParser 类

### 5.1 类定义
```python
class DateParser:
    """日期解析和验证类"""
    
    def __init__(self, config: Dict):
        """初始化日期解析器"""
```

### 5.2 主要方法
```python
def parse_dates_from_text(self, text_results: List[TextResult]) -> List[str]:
    """从文本结果中解析日期
    
    Args:
        text_results (List[TextResult]): OCR文本结果
        
    Returns:
        List[str]: 解析出的日期列表
    """

def validate_date(self, date_str: str) -> bool:
    """验证日期有效性
    
    Args:
        date_str (str): 日期字符串
        
    Returns:
        bool: 是否为有效日期
    """

def standardize_format(self, date_str: str) -> str:
    """标准化日期格式
    
    Args:
        date_str (str): 原始日期字符串
        
    Returns:
        str: 标准化后的日期字符串 (YYYY-MM-DD)
    """
```

## 6. ImageProcessor 类

### 6.1 类定义
```python
class ImageProcessor:
    """图像预处理类"""
    
    def __init__(self, config: Dict):
        """初始化图像处理器"""
```

### 6.2 主要方法
```python
def load_image(self, image_path: str) -> np.ndarray:
    """加载图像文件
    
    Args:
        image_path (str): 图像文件路径
        
    Returns:
        np.ndarray: 图像数组
    """

def enhance_image(self, image: np.ndarray) -> np.ndarray:
    """图像增强处理
    
    Args:
        image (np.ndarray): 输入图像
        
    Returns:
        np.ndarray: 增强后的图像
    """

def correct_rotation(self, image: np.ndarray, angle: float) -> np.ndarray:
    """旋转校正
    
    Args:
        image (np.ndarray): 输入图像
        angle (float): 旋转角度
        
    Returns:
        np.ndarray: 校正后的图像
    """
```

## 7. 配置参数

### 7.1 默认配置
```python
DEFAULT_CONFIG = {
    "ocr": {
        "engine": "paddleocr",
        "language": "ch",
        "use_gpu": False,
        "confidence_threshold": 0.8,
        "use_angle_cls": True
    },
    "image_processing": {
        "max_size": 1920,
        "enhance_contrast": True,
        "denoise": True,
        "auto_rotate": True
    },
    "date_parsing": {
        "formats": [
            r"\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}",
            r"\d{8}",
            r"\d{4}年\d{1,2}月\d{1,2}日"
        ],
        "year_range": [2020, 2030],
        "strict_validation": True
    },
    "performance": {
        "max_workers": 4,
        "batch_size": 10,
        "cache_enabled": True,
        "timeout": 30
    }
}
```

## 8. 异常处理

### 8.1 异常类型
```python
class OCRException(Exception):
    """OCR相关异常基类"""
    pass

class ImageProcessingError(OCRException):
    """图像处理异常"""
    pass

class DateParsingError(OCRException):
    """日期解析异常"""
    pass

class ConfigurationError(OCRException):
    """配置异常"""
    pass
```

## 9. 使用示例

### 9.1 基础使用
```python
from core.date_recognizer import DateRecognizer

# 初始化识别器
recognizer = DateRecognizer()

# 识别单张图片
result = recognizer.recognize_single("test.jpg")
if result.success:
    print(f"识别到日期: {result.dates_found}")
    print(f"置信度: {result.confidence:.2f}")
else:
    print(f"识别失败: {result.warning_message}")
```

### 9.2 批量处理
```python
# 批量处理文件夹
batch_result = recognizer.recognize_folder("./images")

# 生成报告
report = batch_result.generate_report()
print(report)

# 获取失败的结果
failed_results = batch_result.get_failed_results()
for result in failed_results:
    print(f"失败文件: {result.image_path}")
    print(f"错误信息: {result.warning_message}")
```

### 9.3 自定义配置
```python
# 自定义配置
custom_config = {
    "ocr": {
        "confidence_threshold": 0.9,
        "use_gpu": True
    },
    "performance": {
        "max_workers": 8
    }
}

recognizer = DateRecognizer(custom_config)
```

## 10. 性能优化建议

### 10.1 图像预处理
- 适当调整图像尺寸，避免过大图像
- 启用图像增强功能提高识别精度
- 使用GPU加速(如果可用)

### 10.2 批量处理
- 合理设置并行工作线程数
- 启用结果缓存避免重复处理
- 分批处理大量文件避免内存溢出

### 10.3 配置优化
- 根据硬件配置调整参数
- 在精度和速度之间找到平衡
- 定期更新OCR模型获得更好性能
