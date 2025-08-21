#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品包装生产日期识别系统 V1.0 主程序

提供GUI界面的日期识别应用程序
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入应用程序模块
from utils.config_loader import get_config
from utils.logger import setup_logging
from v1.gui.main_window import create_main_window


class Application:
    """应用程序主类"""
    
    def __init__(self):
        """初始化应用程序"""
        self.config = None
        self.logger = None
        self.main_window = None
        
        # 初始化应用程序
        self._initialize()
    
    def _initialize(self):
        """初始化应用程序组件"""
        try:
            # 1. 加载配置
            self.config = get_config()
            
            # 2. 设置日志
            self.logger = setup_logging()
            self.logger.info("=" * 60)
            self.logger.info("商品包装生产日期识别系统 V1.0 启动")
            self.logger.info("=" * 60)
            
            # 3. 记录系统信息
            self._log_system_info()
            
            # 4. 验证环境
            self._verify_environment()
            
            self.logger.info("应用程序初始化完成")
            
        except Exception as e:
            print(f"应用程序初始化失败: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    def _log_system_info(self):
        """记录系统信息"""
        import platform
        import tkinter as tk
        
        self.logger.info(f"Python版本: {sys.version}")
        self.logger.info(f"操作系统: {platform.system()} {platform.release()}")
        self.logger.info(f"架构: {platform.machine()}")
        self.logger.info(f"工作目录: {os.getcwd()}")
        
        # 检查Tkinter版本
        try:
            root = tk.Tk()
            tk_version = root.tk.call('info', 'patchlevel')
            root.destroy()
            self.logger.info(f"Tkinter版本: {tk_version}")
        except Exception as e:
            self.logger.warning(f"无法获取Tkinter版本: {e}")
    
    def _verify_environment(self):
        """验证运行环境"""
        # 检查必要的目录
        required_dirs = ['logs', 'config']
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"创建目录: {dir_path}")
        
        # 检查配置文件
        config_file = project_root / 'config' / 'settings.yaml'
        if config_file.exists():
            self.logger.info(f"配置文件: {config_file}")
        else:
            self.logger.warning(f"配置文件不存在，使用默认配置: {config_file}")
        
        # 检查测试图像目录
        test_image_dir = project_root / 'test_image'
        if test_image_dir.exists():
            image_count = len(list(test_image_dir.glob('*')))
            self.logger.info(f"测试图像目录: {test_image_dir} ({image_count} 个文件)")
        else:
            self.logger.info("测试图像目录不存在")
        
        # 检查关键模块
        try:
            import tkinter
            self.logger.info("Tkinter模块: 可用")
        except ImportError:
            self.logger.error("Tkinter模块不可用")
            raise
        
        try:
            import cv2
            self.logger.info(f"OpenCV版本: {cv2.__version__}")
        except ImportError:
            self.logger.warning("OpenCV不可用，某些图像处理功能可能受限")
        
        try:
            import PIL
            self.logger.info(f"Pillow版本: {PIL.__version__}")
        except ImportError:
            self.logger.warning("Pillow不可用，某些图像处理功能可能受限")
        
        # 显示OCR引擎信息
        try:
            from core.ocr_engine import get_ocr_engine
            ocr_engine = get_ocr_engine()
            engine_info = ocr_engine.get_engine_info()

            self.logger.info("OCR引擎信息:")
            self.logger.info(f"  引擎类型: {engine_info.get('engine_type', 'unknown')}")

            if 'available_engines' in engine_info:
                available = ', '.join(engine_info['available_engines'])
                self.logger.info(f"  可用引擎: {available}")

            if 'ocr_stats' in engine_info:
                stats = engine_info['ocr_stats']
                self.logger.info(f"  使用统计: {stats}")

        except Exception as e:
            self.logger.warning(f"获取OCR引擎信息失败: {e}")
            self.logger.info("OCR引擎: 混合OCR (真正OCR + 智能模拟OCR)")
    
    def run(self):
        """运行应用程序"""
        try:
            self.logger.info("启动GUI界面...")
            
            # 创建主窗口
            self.main_window = create_main_window()
            
            # 运行主循环
            self.main_window.run()
            
        except KeyboardInterrupt:
            self.logger.info("用户中断程序")
        except Exception as e:
            self.logger.error(f"应用程序运行时错误: {e}")
            traceback.print_exc()
            
            # 显示错误对话框
            try:
                import tkinter.messagebox as messagebox
                messagebox.showerror("错误", f"应用程序发生错误:\n{e}")
            except:
                pass
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            self.logger.info("正在清理资源...")
            
            # 清理主窗口
            if self.main_window:
                try:
                    self.main_window.root.quit()
                except:
                    pass
            
            self.logger.info("应用程序已退出")
            
        except Exception as e:
            print(f"清理资源时发生错误: {e}")


def check_dependencies():
    """检查依赖项"""
    missing_deps = []
    
    # 检查必需的依赖
    required_deps = [
        ('tkinter', 'Python标准库Tkinter'),
        ('PIL', 'Pillow图像处理库'),
        ('numpy', 'NumPy数值计算库'),
        ('yaml', 'PyYAML配置文件库')
    ]
    
    for module_name, description in required_deps:
        try:
            __import__(module_name)
        except ImportError:
            missing_deps.append(f"- {description} ({module_name})")
    
    # 检查可选的依赖
    optional_deps = [
        ('cv2', 'OpenCV图像处理库'),
        # 注意：PaddleOCR已被智能模拟OCR替代，无需检查
    ]
    
    missing_optional = []
    for module_name, description in optional_deps:
        try:
            __import__(module_name)
        except ImportError:
            missing_optional.append(f"- {description} ({module_name})")
    
    if missing_deps:
        print("错误: 缺少必需的依赖项:")
        for dep in missing_deps:
            print(dep)
        print("\n请运行以下命令安装:")
        print("pip install -r requirements.txt")
        return False
    
    if missing_optional:
        print("警告: 缺少可选的依赖项:")
        for dep in missing_optional:
            print(dep)
        print("\n这些依赖项不是必需的，但建议安装以获得完整功能。")
    
    return True


def main():
    """主函数"""
    print("商品包装生产日期识别系统 V1.0")
    print("=" * 50)
    
    # 检查依赖项
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # 创建并运行应用程序
        app = Application()
        app.run()
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
