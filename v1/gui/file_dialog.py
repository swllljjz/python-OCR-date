"""
文件对话框模块

提供文件选择、文件夹选择、文件预览等功能
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import logging
from typing import List, Optional, Tuple
from pathlib import Path

from utils.config_loader import get_config

logger = logging.getLogger(__name__)


class FileDialogManager:
    """文件对话框管理器
    
    提供统一的文件选择和管理功能
    """
    
    def __init__(self, parent: tk.Tk):
        """初始化文件对话框管理器
        
        Args:
            parent: 父窗口
        """
        self.parent = parent
        self.config = get_config().config
        
        # 图像处理配置
        image_config = self.config.get('image_processing', {})
        self.supported_formats = image_config.get('supported_formats', 
                                                ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'])
        
        # 构建文件类型过滤器
        self.file_types = self._build_file_types()
        
        # 记住上次使用的目录 - 优先使用项目目录
        self.last_directory = self._get_initial_directory()
        
        logger.info("文件对话框管理器初始化完成")

    def _get_initial_directory(self) -> str:
        """获取初始目录

        优先级：
        1. 项目根目录下的 test_image 文件夹
        2. 项目根目录
        3. 用户主目录

        Returns:
            初始目录路径
        """
        try:
            # 获取项目根目录（假设当前文件在 v1/gui/ 下）
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent  # 向上三级到项目根目录

            # 检查 test_image 文件夹
            test_image_dir = project_root / "test_image"
            if test_image_dir.exists() and test_image_dir.is_dir():
                logger.info(f"使用测试图片目录作为初始路径: {test_image_dir}")
                return str(test_image_dir)

            # 检查项目根目录
            if project_root.exists() and project_root.is_dir():
                logger.info(f"使用项目根目录作为初始路径: {project_root}")
                return str(project_root)

        except Exception as e:
            logger.warning(f"获取项目目录失败: {e}")

        # 备选：使用用户主目录
        home_dir = os.path.expanduser("~")
        logger.info(f"使用用户主目录作为初始路径: {home_dir}")
        return home_dir
    
    def _build_file_types(self) -> List[Tuple[str, str]]:
        """构建文件类型过滤器
        
        Returns:
            文件类型列表
        """
        file_types = []
        
        # 所有支持的图像格式
        all_extensions = " ".join([f"*{ext}" for ext in self.supported_formats])
        file_types.append(("所有支持的图像", all_extensions))
        
        # 具体格式
        format_map = {
            '.jpg': "JPEG图像",
            '.jpeg': "JPEG图像", 
            '.png': "PNG图像",
            '.bmp': "BMP图像",
            '.tiff': "TIFF图像",
            '.webp': "WebP图像"
        }
        
        for ext in self.supported_formats:
            if ext in format_map:
                file_types.append((format_map[ext], f"*{ext}"))
        
        # 所有文件
        file_types.append(("所有文件", "*.*"))
        
        return file_types
    
    def select_files(self, title: str = "选择图像文件") -> List[str]:
        """选择多个文件
        
        Args:
            title: 对话框标题
            
        Returns:
            选择的文件路径列表
        """
        try:
            files = filedialog.askopenfilenames(
                parent=self.parent,
                title=title,
                initialdir=self.last_directory,
                filetypes=self.file_types
            )
            
            if files:
                # 更新最后使用的目录
                self.last_directory = os.path.dirname(files[0])
                
                # 验证文件
                valid_files = self._validate_selected_files(files)
                
                logger.info(f"选择了 {len(valid_files)} 个有效文件")
                return valid_files
            
            return []
            
        except Exception as e:
            logger.error(f"文件选择失败: {e}")
            messagebox.showerror("错误", f"文件选择失败: {e}")
            return []
    
    def select_single_file(self, title: str = "选择图像文件") -> Optional[str]:
        """选择单个文件
        
        Args:
            title: 对话框标题
            
        Returns:
            选择的文件路径，如果取消则返回None
        """
        try:
            file_path = filedialog.askopenfilename(
                parent=self.parent,
                title=title,
                initialdir=self.last_directory,
                filetypes=self.file_types
            )
            
            if file_path:
                # 更新最后使用的目录
                self.last_directory = os.path.dirname(file_path)
                
                # 验证文件
                if self._is_valid_image_file(file_path):
                    logger.info(f"选择了文件: {file_path}")
                    return file_path
                else:
                    messagebox.showwarning("警告", "选择的文件不是有效的图像文件")
            
            return None
            
        except Exception as e:
            logger.error(f"文件选择失败: {e}")
            messagebox.showerror("错误", f"文件选择失败: {e}")
            return None
    
    def select_folder(self, title: str = "选择包含图像的文件夹") -> Optional[str]:
        """选择文件夹
        
        Args:
            title: 对话框标题
            
        Returns:
            选择的文件夹路径，如果取消则返回None
        """
        try:
            folder_path = filedialog.askdirectory(
                parent=self.parent,
                title=title,
                initialdir=self.last_directory
            )
            
            if folder_path:
                # 更新最后使用的目录
                self.last_directory = folder_path
                
                logger.info(f"选择了文件夹: {folder_path}")
                return folder_path
            
            return None
            
        except Exception as e:
            logger.error(f"文件夹选择失败: {e}")
            messagebox.showerror("错误", f"文件夹选择失败: {e}")
            return None
    
    def save_file(self, title: str = "保存文件", 
                  default_extension: str = ".txt",
                  file_types: Optional[List[Tuple[str, str]]] = None) -> Optional[str]:
        """保存文件对话框
        
        Args:
            title: 对话框标题
            default_extension: 默认扩展名
            file_types: 文件类型列表
            
        Returns:
            保存的文件路径，如果取消则返回None
        """
        try:
            if file_types is None:
                file_types = [
                    ("文本文件", "*.txt"),
                    ("CSV文件", "*.csv"),
                    ("JSON文件", "*.json"),
                    ("所有文件", "*.*")
                ]
            
            file_path = filedialog.asksaveasfilename(
                parent=self.parent,
                title=title,
                initialdir=self.last_directory,
                defaultextension=default_extension,
                filetypes=file_types
            )
            
            if file_path:
                # 更新最后使用的目录
                self.last_directory = os.path.dirname(file_path)
                
                logger.info(f"选择保存路径: {file_path}")
                return file_path
            
            return None
            
        except Exception as e:
            logger.error(f"保存文件对话框失败: {e}")
            messagebox.showerror("错误", f"保存文件对话框失败: {e}")
            return None
    
    def _validate_selected_files(self, file_paths: List[str]) -> List[str]:
        """验证选择的文件
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            有效的文件路径列表
        """
        valid_files = []
        invalid_files = []
        
        for file_path in file_paths:
            if self._is_valid_image_file(file_path):
                valid_files.append(file_path)
            else:
                invalid_files.append(file_path)
        
        # 如果有无效文件，显示警告
        if invalid_files:
            invalid_count = len(invalid_files)
            if invalid_count <= 5:
                # 显示具体的无效文件
                invalid_names = [os.path.basename(f) for f in invalid_files]
                message = f"以下 {invalid_count} 个文件不是有效的图像文件:\n" + "\n".join(invalid_names)
            else:
                # 只显示数量
                message = f"有 {invalid_count} 个文件不是有效的图像文件"
            
            messagebox.showwarning("警告", message)
        
        return valid_files
    
    def _is_valid_image_file(self, file_path: str) -> bool:
        """检查是否为有效的图像文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为有效的图像文件
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False
            
            # 检查是否为文件
            if not os.path.isfile(file_path):
                return False
            
            # 检查文件扩展名
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                return False
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
            
            # 检查文件大小限制（100MB）
            max_size = 100 * 1024 * 1024
            if file_size > max_size:
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"文件验证失败: {file_path}, 错误: {e}")
            return False
    
    def get_file_info_preview(self, file_path: str) -> str:
        """获取文件信息预览
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字符串
        """
        try:
            if not os.path.exists(file_path):
                return "文件不存在"
            
            file_stat = os.stat(file_path)
            file_path_obj = Path(file_path)
            
            # 格式化文件大小
            size_bytes = file_stat.st_size
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            
            # 格式化修改时间
            import datetime
            mod_time = datetime.datetime.fromtimestamp(file_stat.st_mtime)
            mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            
            info = f"""文件信息:
文件名: {file_path_obj.name}
路径: {file_path}
大小: {size_str}
格式: {file_path_obj.suffix.upper()}
修改时间: {mod_time_str}
"""
            return info
            
        except Exception as e:
            return f"获取文件信息失败: {e}"
    
    def show_file_info_dialog(self, file_path: str):
        """显示文件信息对话框
        
        Args:
            file_path: 文件路径
        """
        info = self.get_file_info_preview(file_path)
        messagebox.showinfo("文件信息", info)
    
    def confirm_overwrite(self, file_path: str) -> bool:
        """确认覆盖文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否确认覆盖
        """
        if os.path.exists(file_path):
            return messagebox.askyesno(
                "确认覆盖", 
                f"文件 '{os.path.basename(file_path)}' 已存在，是否覆盖？"
            )
        return True
    
    def get_last_directory(self) -> str:
        """获取最后使用的目录
        
        Returns:
            最后使用的目录路径
        """
        return self.last_directory
    
    def set_last_directory(self, directory: str):
        """设置最后使用的目录
        
        Args:
            directory: 目录路径
        """
        if os.path.exists(directory) and os.path.isdir(directory):
            self.last_directory = directory
            logger.debug(f"更新最后使用的目录: {directory}")


# 工厂函数
def create_file_dialog_manager(parent: tk.Tk) -> FileDialogManager:
    """创建文件对话框管理器实例
    
    Args:
        parent: 父窗口
        
    Returns:
        文件对话框管理器实例
    """
    return FileDialogManager(parent)
