"""
图像处理模块

提供图像预处理、增强、旋转校正等功能
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Union
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import math

from utils.config_loader import get_config
from utils.validators import validate_image_file, validate_image_size

logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """图像处理异常"""
    pass


class ImageProcessor:
    """图像预处理类
    
    负责图像加载、预处理、增强和旋转校正
    """
    
    def __init__(self, config: Optional[dict] = None):
        """初始化图像处理器
        
        Args:
            config: 配置字典，如果为None则使用全局配置
        """
        if config is None:
            app_config = get_config()
            self.config = app_config.get_section('image_processing')
        else:
            self.config = config.get('image_processing', {})
        
        # 设置默认参数
        self.max_width = self.config.get('max_width', 1920)
        self.max_height = self.config.get('max_height', 1080)
        self.enhance_contrast = self.config.get('enhance_contrast', True)
        self.contrast_factor = self.config.get('contrast_factor', 1.2)
        self.denoise = self.config.get('denoise', True)
        self.denoise_strength = self.config.get('denoise_strength', 3)
        self.auto_rotate = self.config.get('auto_rotate', True)
        self.rotation_threshold = self.config.get('rotation_threshold', 5.0)
        self.supported_formats = self.config.get('supported_formats', 
                                                ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'])
        
        logger.info("图像处理器初始化完成")
    
    def load_image(self, image_path: str) -> np.ndarray:
        """加载图像文件
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            图像数组 (BGR格式)
            
        Raises:
            ImageProcessingError: 图像加载失败
        """
        try:
            # 验证图像文件
            validate_image_file(image_path, self.supported_formats)
            
            # 使用OpenCV加载图像
            image = cv2.imread(image_path)
            
            if image is None:
                # 尝试使用PIL加载
                try:
                    pil_image = Image.open(image_path)
                    # 转换为RGB然后转为BGR (OpenCV格式)
                    if pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')
                    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    raise ImageProcessingError(f"无法加载图像文件: {image_path}, 错误: {e}")
            
            # 验证图像尺寸
            height, width = image.shape[:2]
            validate_image_size(width, height)
            
            logger.info(f"图像加载成功: {image_path}, 尺寸: {width}x{height}")
            return image
            
        except Exception as e:
            logger.error(f"图像加载失败: {image_path}, 错误: {e}")
            raise ImageProcessingError(f"图像加载失败: {e}")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理主流程
        
        Args:
            image: 输入图像
            
        Returns:
            预处理后的图像
        """
        try:
            logger.debug("开始图像预处理")
            
            # 1. 尺寸调整
            processed_image = self.resize_image(image)
            
            # 2. 图像增强
            if self.enhance_contrast:
                processed_image = self.enhance_image(processed_image)
            
            # 3. 降噪处理
            if self.denoise:
                processed_image = self.denoise_image(processed_image)
            
            # 4. 旋转检测和校正
            if self.auto_rotate:
                angle = self.detect_text_orientation(processed_image)
                if abs(angle) > self.rotation_threshold:
                    processed_image = self.correct_rotation(processed_image, angle)
                    logger.info(f"图像旋转校正: {angle:.2f}度")
            
            logger.debug("图像预处理完成")
            return processed_image
            
        except Exception as e:
            logger.error(f"图像预处理失败: {e}")
            raise ImageProcessingError(f"图像预处理失败: {e}")
    
    def resize_image(self, image: np.ndarray, 
                    target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """图像尺寸调整
        
        Args:
            image: 输入图像
            target_size: 目标尺寸 (width, height)，如果为None则使用配置的最大尺寸
            
        Returns:
            调整后的图像
        """
        height, width = image.shape[:2]
        
        if target_size is None:
            # 计算缩放比例，保持宽高比
            scale_w = self.max_width / width
            scale_h = self.max_height / height
            scale = min(scale_w, scale_h, 1.0)  # 不放大图像
            
            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                target_size = (new_width, new_height)
            else:
                return image  # 不需要调整
        
        # 使用高质量插值方法
        resized = cv2.resize(image, target_size, interpolation=cv2.INTER_LANCZOS4)
        
        logger.debug(f"图像尺寸调整: {width}x{height} -> {target_size[0]}x{target_size[1]}")
        return resized
    
    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """图像增强处理
        
        Args:
            image: 输入图像
            
        Returns:
            增强后的图像
        """
        try:
            # 转换为PIL图像进行增强
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            
            # 对比度增强
            enhancer = ImageEnhance.Contrast(pil_image)
            enhanced = enhancer.enhance(self.contrast_factor)
            
            # 锐度增强
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(1.1)
            
            # 转换回OpenCV格式
            enhanced_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
            
            logger.debug("图像增强完成")
            return enhanced_cv
            
        except Exception as e:
            logger.warning(f"图像增强失败，使用原图像: {e}")
            return image
    
    def denoise_image(self, image: np.ndarray) -> np.ndarray:
        """图像降噪处理
        
        Args:
            image: 输入图像
            
        Returns:
            降噪后的图像
        """
        try:
            # 使用非局部均值降噪
            denoised = cv2.fastNlMeansDenoisingColored(
                image, None, 
                h=self.denoise_strength, 
                hColor=self.denoise_strength,
                templateWindowSize=7, 
                searchWindowSize=21
            )
            
            logger.debug("图像降噪完成")
            return denoised
            
        except Exception as e:
            logger.warning(f"图像降噪失败，使用原图像: {e}")
            return image
    
    def detect_text_orientation(self, image: np.ndarray) -> float:
        """检测文本方向
        
        Args:
            image: 输入图像
            
        Returns:
            旋转角度（度）
        """
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 边缘检测
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # 霍夫直线检测
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is None:
                return 0.0
            
            # 计算主要方向
            angles = []
            for line in lines:
                rho, theta = line[0]
                angle = theta * 180 / np.pi
                
                # 将角度标准化到 [-90, 90] 范围
                if angle > 90:
                    angle -= 180
                elif angle < -90:
                    angle += 180
                
                angles.append(angle)
            
            if not angles:
                return 0.0
            
            # 使用中位数作为主要角度
            median_angle = np.median(angles)
            
            logger.debug(f"检测到文本方向: {median_angle:.2f}度")
            return median_angle
            
        except Exception as e:
            logger.warning(f"文本方向检测失败: {e}")
            return 0.0
    
    def correct_rotation(self, image: np.ndarray, angle: float) -> np.ndarray:
        """旋转校正
        
        Args:
            image: 输入图像
            angle: 旋转角度（度）
            
        Returns:
            校正后的图像
        """
        try:
            height, width = image.shape[:2]
            center = (width // 2, height // 2)
            
            # 创建旋转矩阵
            rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
            
            # 计算新的图像尺寸
            cos_angle = abs(rotation_matrix[0, 0])
            sin_angle = abs(rotation_matrix[0, 1])
            
            new_width = int((height * sin_angle) + (width * cos_angle))
            new_height = int((height * cos_angle) + (width * sin_angle))
            
            # 调整旋转中心
            rotation_matrix[0, 2] += (new_width / 2) - center[0]
            rotation_matrix[1, 2] += (new_height / 2) - center[1]
            
            # 执行旋转
            rotated = cv2.warpAffine(
                image, rotation_matrix, (new_width, new_height),
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255)  # 白色背景
            )
            
            logger.debug(f"图像旋转校正完成: {angle:.2f}度")
            return rotated
            
        except Exception as e:
            logger.warning(f"图像旋转校正失败，使用原图像: {e}")
            return image
    
    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """转换为灰度图
        
        Args:
            image: 输入图像
            
        Returns:
            灰度图像
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        return gray
    
    def adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """自适应阈值处理
        
        Args:
            image: 输入图像（灰度图）
            
        Returns:
            二值化图像
        """
        try:
            # 确保是灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # 自适应阈值
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            return binary
            
        except Exception as e:
            logger.warning(f"自适应阈值处理失败: {e}")
            return image
    
    def get_image_info(self, image: np.ndarray) -> dict:
        """获取图像信息
        
        Args:
            image: 输入图像
            
        Returns:
            图像信息字典
        """
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) == 3 else 1
        
        return {
            'width': width,
            'height': height,
            'channels': channels,
            'dtype': str(image.dtype),
            'size': image.size,
            'shape': image.shape
        }
    
    def save_image(self, image: np.ndarray, output_path: str, 
                  quality: int = 95) -> bool:
        """保存图像
        
        Args:
            image: 图像数组
            output_path: 输出路径
            quality: 图像质量 (1-100)
            
        Returns:
            是否保存成功
        """
        try:
            # 确保输出目录存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            success = cv2.imwrite(output_path, image, 
                                [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            if success:
                logger.info(f"图像保存成功: {output_path}")
            else:
                logger.error(f"图像保存失败: {output_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"图像保存异常: {output_path}, 错误: {e}")
            return False


# 工厂函数
def create_image_processor(config: Optional[dict] = None) -> ImageProcessor:
    """创建图像处理器实例

    Args:
        config: 配置字典

    Returns:
        图像处理器实例
    """
    return ImageProcessor(config)
