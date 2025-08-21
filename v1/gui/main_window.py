"""
主窗口模块

提供应用程序的主界面，包括菜单栏、工具栏、状态栏等
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import threading
from typing import Optional, Dict, Any, List

from utils.config_loader import get_config
from utils.logger import get_logger
from v1.gui.file_dialog import FileDialogManager
from v1.gui.result_display import ResultDisplayWidget
from v1.handlers.file_handler import create_file_handler, create_progress_tracker
from v1.handlers.batch_processor import create_batch_processor

logger = get_logger(__name__)


class MainWindow:
    """主窗口类
    
    应用程序的主界面，整合所有功能模块
    """
    
    def __init__(self):
        """初始化主窗口"""
        self.config = get_config().config
        self.gui_config = self.config.get('gui', {})
        
        # 创建主窗口
        self.root = tk.Tk()
        self._setup_window()
        
        # 初始化组件
        self.file_handler = create_file_handler()
        self.batch_processor = create_batch_processor()
        self.file_dialog_manager = FileDialogManager(self.root)
        
        # 创建界面元素
        self._create_menu()
        self._create_toolbar()
        self._create_main_frame()
        self._create_status_bar()
        
        # 状态变量
        self.current_files = []
        self.processing_thread = None
        self.is_processing = False
        
        logger.info("主窗口初始化完成")
    
    def _setup_window(self):
        """设置窗口属性"""
        # 窗口标题
        title = self.gui_config.get('window_title', '商品包装日期识别系统 V1.0')
        self.root.title(title)
        
        # 窗口大小
        window_size = self.gui_config.get('window_size', [1200, 800])
        self.root.geometry(f"{window_size[0]}x{window_size[1]}")
        
        # 窗口居中
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (window_size[0] // 2)
        y = (self.root.winfo_screenheight() // 2) - (window_size[1] // 2)
        self.root.geometry(f"{window_size[0]}x{window_size[1]}+{x}+{y}")
        
        # 窗口图标（如果有的话）
        try:
            # self.root.iconbitmap('icon.ico')  # 可以添加图标
            pass
        except:
            pass
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 设置最小尺寸
        self.root.minsize(800, 600)
        
        # 是否可调整大小
        resizable = self.gui_config.get('resizable', True)
        self.root.resizable(resizable, resizable)
    
    def _create_menu(self):
        """创建菜单栏"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # 文件菜单
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择文件...", command=self._select_files, accelerator="Ctrl+O")
        file_menu.add_command(label="选择文件夹...", command=self._select_folder, accelerator="Ctrl+Shift+O")
        file_menu.add_separator()
        file_menu.add_command(label="清空列表", command=self._clear_files)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_closing, accelerator="Ctrl+Q")
        
        # 处理菜单
        process_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="处理", menu=process_menu)
        process_menu.add_command(label="开始识别", command=self._start_processing, accelerator="F5")
        process_menu.add_command(label="停止处理", command=self._stop_processing, accelerator="Esc")
        process_menu.add_separator()
        process_menu.add_command(label="清空缓存", command=self._clear_cache)
        
        # 查看菜单
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="查看", menu=view_menu)
        view_menu.add_command(label="刷新", command=self._refresh_display, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="显示统计信息", command=self._show_stats)
        
        # 帮助菜单
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
        
        # 绑定快捷键
        self.root.bind('<Control-o>', lambda e: self._select_files())
        self.root.bind('<Control-Shift-O>', lambda e: self._select_folder())
        self.root.bind('<Control-q>', lambda e: self._on_closing())
        self.root.bind('<F5>', lambda e: self._start_processing())
        self.root.bind('<Escape>', lambda e: self._stop_processing())
    
    def _create_toolbar(self):
        """创建工具栏"""
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # 文件操作按钮
        ttk.Button(self.toolbar, text="选择文件", command=self._select_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="选择文件夹", command=self._select_folder).pack(side=tk.LEFT, padx=2)
        
        # 分隔符
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 处理按钮
        self.start_button = ttk.Button(self.toolbar, text="开始识别", command=self._start_processing)
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = ttk.Button(self.toolbar, text="停止处理", command=self._stop_processing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        # 分隔符
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 清空按钮
        ttk.Button(self.toolbar, text="清空列表", command=self._clear_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="清空缓存", command=self._clear_cache).pack(side=tk.LEFT, padx=2)
        
        # 右侧信息
        self.file_count_label = ttk.Label(self.toolbar, text="文件数: 0")
        self.file_count_label.pack(side=tk.RIGHT, padx=5)
    
    def _create_main_frame(self):
        """创建主框架"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建左右分割面板
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左侧文件列表框架
        self.left_frame = ttk.LabelFrame(self.paned_window, text="文件列表", padding=5)
        self.paned_window.add(self.left_frame, weight=1)
        
        # 文件列表
        self._create_file_list()
        
        # 右侧结果显示框架
        self.right_frame = ttk.LabelFrame(self.paned_window, text="识别结果", padding=5)
        self.paned_window.add(self.right_frame, weight=2)
        
        # 结果显示组件
        self.result_display = ResultDisplayWidget(self.right_frame)
        self.result_display.pack(fill=tk.BOTH, expand=True)
    
    def _create_file_list(self):
        """创建文件列表"""
        # 创建Treeview
        columns = ('文件名', '大小', '状态')
        self.file_tree = ttk.Treeview(self.left_frame, columns=columns, show='tree headings')
        
        # 设置列标题
        self.file_tree.heading('#0', text='路径')
        self.file_tree.heading('文件名', text='文件名')
        self.file_tree.heading('大小', text='大小')
        self.file_tree.heading('状态', text='状态')
        
        # 设置列宽
        self.file_tree.column('#0', width=200)
        self.file_tree.column('文件名', width=150)
        self.file_tree.column('大小', width=80)
        self.file_tree.column('状态', width=100)
        
        # 滚动条
        file_scrollbar = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=file_scrollbar.set)
        
        # 布局
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.file_tree.bind('<<TreeviewSelect>>', self._on_file_select)
        self.file_tree.bind('<Double-1>', self._on_file_double_click)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 状态标签
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # OCR引擎信息标签
        self.ocr_info_label = ttk.Label(self.status_frame, text="OCR: PaddleOCR", foreground="blue")
        self.ocr_info_label.pack(side=tk.LEFT, padx=10)

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.status_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=5, pady=2)

        # 进度标签
        self.progress_label = ttk.Label(self.status_frame, text="")
        self.progress_label.pack(side=tk.RIGHT, padx=5)
    
    def _select_files(self):
        """选择文件"""
        try:
            files = self.file_dialog_manager.select_files()
            if files:
                self._add_files(files)
        except Exception as e:
            logger.error(f"选择文件失败: {e}")
            messagebox.showerror("错误", f"选择文件失败: {e}")
    
    def _select_folder(self):
        """选择文件夹"""
        try:
            folder = self.file_dialog_manager.select_folder()
            if folder:
                # 扫描文件夹
                self._scan_folder(folder)
        except Exception as e:
            logger.error(f"选择文件夹失败: {e}")
            messagebox.showerror("错误", f"选择文件夹失败: {e}")
    
    def _scan_folder(self, folder_path: str):
        """扫描文件夹"""
        try:
            self._update_status("正在扫描文件夹...")
            
            # 创建进度跟踪器
            progress_tracker = create_progress_tracker()
            progress_tracker.add_callback(self._update_scan_progress)
            
            # 扫描文件
            files = self.file_handler.scan_directory(folder_path, True, progress_tracker)
            
            if files:
                self._add_files(files)
                self._update_status(f"扫描完成，找到 {len(files)} 个文件")
            else:
                self._update_status("未找到图像文件")
                messagebox.showinfo("信息", "在选择的文件夹中未找到支持的图像文件")
                
        except Exception as e:
            logger.error(f"扫描文件夹失败: {e}")
            messagebox.showerror("错误", f"扫描文件夹失败: {e}")
            self._update_status("扫描失败")
    
    def _add_files(self, file_paths: List[str]):
        """添加文件到列表"""
        for file_path in file_paths:
            if file_path not in self.current_files:
                self.current_files.append(file_path)
                
                # 获取文件信息
                file_info = self.file_handler.get_file_info(file_path)
                
                # 添加到树形视图
                file_name = file_info.get('name', 'Unknown')
                file_size = f"{file_info.get('size_mb', 0):.1f} MB"
                
                self.file_tree.insert('', tk.END, 
                                    text=file_path,
                                    values=(file_name, file_size, '待处理'))
        
        # 更新文件计数
        self._update_file_count()
        self._update_status(f"已添加 {len(file_paths)} 个文件")
    
    def _clear_files(self):
        """清空文件列表"""
        self.current_files.clear()
        self.file_tree.delete(*self.file_tree.get_children())
        self.result_display.clear()
        self._update_file_count()
        self._update_status("文件列表已清空")
    
    def _start_processing(self):
        """开始处理"""
        if not self.current_files:
            messagebox.showwarning("警告", "请先选择要处理的文件")
            return
        
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self._process_files)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _process_files(self):
        """处理文件（在后台线程中运行）"""
        try:
            self.is_processing = True
            self._update_ui_processing_state(True)
            
            # 批量处理
            batch_result = self.batch_processor.process_files(
                self.current_files, 
                self._update_processing_progress
            )
            
            # 更新结果显示
            self.root.after(0, lambda: self.result_display.show_batch_result(batch_result))
            self.root.after(0, lambda: self._update_status(f"处理完成: {batch_result.success_rate:.1%} 成功率"))
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"处理失败: {e}"))
            self.root.after(0, lambda: self._update_status("处理失败"))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self._update_ui_processing_state(False))
    
    def _stop_processing(self):
        """停止处理"""
        if self.is_processing:
            self.batch_processor.stop_processing()
            self._update_status("正在停止处理...")
    
    def _clear_cache(self):
        """清空缓存"""
        self.batch_processor.clear_cache()
        self._update_status("缓存已清空")
    
    def _update_ui_processing_state(self, processing: bool):
        """更新UI处理状态"""
        if processing:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_var.set(0)
            self.progress_label.config(text="")
    
    def _update_file_count(self):
        """更新文件计数显示"""
        count = len(self.current_files)
        self.file_count_label.config(text=f"文件数: {count}")
    
    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_label.config(text=message)
        logger.info(f"状态更新: {message}")
    
    def _update_scan_progress(self, progress_info: Dict[str, Any]):
        """更新扫描进度"""
        percentage = progress_info.get('percentage', 0)
        self.progress_var.set(percentage)
        self.progress_label.config(text=f"扫描中... {percentage:.1f}%")
    
    def _update_processing_progress(self, progress_info: Dict[str, Any]):
        """更新处理进度"""
        percentage = progress_info.get('percentage', 0)
        current = progress_info.get('current', 0)
        total = progress_info.get('total', 0)
        
        self.progress_var.set(percentage)
        self.progress_label.config(text=f"处理中... {current}/{total} ({percentage:.1f}%)")
    
    def _on_file_select(self, event):
        """文件选择事件"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            file_path = item['text']
            # 可以在这里显示文件详细信息
    
    def _on_file_double_click(self, event):
        """文件双击事件"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            file_path = item['text']
            # 可以在这里打开文件预览
    
    def _refresh_display(self):
        """刷新显示"""
        self.result_display.refresh()
        self._update_status("显示已刷新")
    
    def _show_stats(self):
        """显示统计信息"""
        stats = self.batch_processor.get_processor_stats()
        stats_text = f"""处理器统计信息:
        
最大工作线程: {stats['max_workers']}
批处理大小: {stats['batch_size']}
正在处理: {'是' if stats['is_processing'] else '否'}

缓存统计:
启用: {'是' if stats['cache_stats']['enabled'] else '否'}
大小: {stats['cache_stats'].get('size', 0)}
最大大小: {stats['cache_stats'].get('max_size', 0)}
使用率: {stats['cache_stats'].get('usage_rate', 0):.1%}
"""
        messagebox.showinfo("统计信息", stats_text)
    
    def _show_help(self):
        """显示帮助"""
        help_text = """使用说明:

1. 选择文件或文件夹
   - 点击"选择文件"按钮选择单个或多个图片文件
   - 点击"选择文件夹"按钮选择包含图片的文件夹

2. 开始识别
   - 点击"开始识别"按钮开始处理
   - 处理过程中可以点击"停止处理"按钮中止

3. 查看结果
   - 识别结果会显示在右侧面板中
   - 双击文件可以查看详细信息

支持的图片格式: JPG, PNG, BMP, TIFF, WebP
"""
        messagebox.showinfo("使用说明", help_text)
    
    def _show_about(self):
        """显示关于信息"""
        about_text = f"""商品包装生产日期识别系统 V1.0

基于PaddleOCR深度学习技术的智能日期识别系统

技术特性:
- 支持多种日期格式识别 (YYYY-MM-DD, YYYY/MM/DD等)
- 智能图像预处理和增强
- PaddleOCR高精度中文识别
- 多线程批量并行处理
- 生产级OCR引擎架构

核心技术:
- OCR引擎: PaddleOCR (专业中文识别)
- 图像处理: OpenCV + 自适应增强
- 界面框架: Python + Tkinter
- 架构设计: 模块化 + 插件式
"""
        messagebox.showinfo("关于", about_text)
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.is_processing:
            if messagebox.askokcancel("确认", "正在处理中，确定要退出吗？"):
                self.batch_processor.stop_processing()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """运行应用程序"""
        logger.info("启动主窗口")
        self.root.mainloop()


# 工厂函数
def create_main_window() -> MainWindow:
    """创建主窗口实例
    
    Returns:
        主窗口实例
    """
    return MainWindow()
