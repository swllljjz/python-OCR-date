"""
结果显示模块

提供识别结果展示、图像显示、预警信息显示等功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from typing import Optional, List, Dict, Any
import json

from core.models import RecognitionResult, BatchResult
from v1.gui.file_dialog import create_file_dialog_manager

logger = logging.getLogger(__name__)


class ResultDisplayWidget(ttk.Frame):
    """结果显示组件
    
    用于显示识别结果、统计信息和详细报告
    """
    
    def __init__(self, parent):
        """初始化结果显示组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        self.current_batch_result = None
        self.current_results = []
        
        # 创建界面
        self._create_widgets()
        
        logger.info("结果显示组件初始化完成")
    
    def _create_widgets(self):
        """创建界面组件"""
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建各个标签页
        self._create_summary_tab()
        self._create_details_tab()
        self._create_report_tab()
        self._create_export_tab()
    
    def _create_summary_tab(self):
        """创建摘要标签页"""
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="摘要")
        
        # 统计信息框架
        stats_frame = ttk.LabelFrame(self.summary_frame, text="统计信息", padding=10)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 统计标签
        self.stats_labels = {}
        stats_items = [
            ("total_files", "总文件数:"),
            ("processed_files", "已处理:"),
            ("success_count", "成功识别:"),
            ("failed_count", "识别失败:"),
            ("success_rate", "成功率:"),
            ("processing_time", "处理时间:")
        ]
        
        for i, (key, label) in enumerate(stats_items):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(stats_frame, text=label).grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            self.stats_labels[key] = ttk.Label(stats_frame, text="--", foreground="blue")
            self.stats_labels[key].grid(row=row, column=col+1, sticky=tk.W, padx=5, pady=2)
        
        # 日期统计框架
        date_stats_frame = ttk.LabelFrame(self.summary_frame, text="识别到的日期", padding=10)
        date_stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 日期列表
        self.date_tree = ttk.Treeview(date_stats_frame, columns=('count', 'files'), show='tree headings')
        self.date_tree.heading('#0', text='日期')
        self.date_tree.heading('count', text='出现次数')
        self.date_tree.heading('files', text='文件数')
        
        self.date_tree.column('#0', width=120)
        self.date_tree.column('count', width=80)
        self.date_tree.column('files', width=80)
        
        # 滚动条
        date_scrollbar = ttk.Scrollbar(date_stats_frame, orient=tk.VERTICAL, command=self.date_tree.yview)
        self.date_tree.configure(yscrollcommand=date_scrollbar.set)
        
        self.date_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        date_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_details_tab(self):
        """创建详细结果标签页"""
        self.details_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.details_frame, text="详细结果")
        
        # 工具栏
        toolbar = ttk.Frame(self.details_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(toolbar, text="显示全部", command=self._show_all_results).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="仅显示成功", command=self._show_success_only).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="仅显示失败", command=self._show_failed_only).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="仅显示警告", command=self._show_warnings_only).pack(side=tk.LEFT, padx=2)
        
        # 结果列表
        columns = ('文件名', '状态', '日期', '置信度', '处理时间', '警告')
        self.result_tree = ttk.Treeview(self.details_frame, columns=columns, show='tree headings')
        
        # 设置列标题
        self.result_tree.heading('#0', text='路径')
        for col in columns:
            self.result_tree.heading(col, text=col)
        
        # 设置列宽
        self.result_tree.column('#0', width=200)
        self.result_tree.column('文件名', width=150)
        self.result_tree.column('状态', width=60)
        self.result_tree.column('日期', width=100)
        self.result_tree.column('置信度', width=80)
        self.result_tree.column('处理时间', width=80)
        self.result_tree.column('警告', width=200)
        
        # 滚动条
        result_scrollbar = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 绑定事件
        self.result_tree.bind('<<TreeviewSelect>>', self._on_result_select)
        self.result_tree.bind('<Double-1>', self._on_result_double_click)
    
    def _create_report_tab(self):
        """创建报告标签页"""
        self.report_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.report_frame, text="报告")
        
        # 工具栏
        report_toolbar = ttk.Frame(self.report_frame)
        report_toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(report_toolbar, text="生成报告", command=self._generate_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(report_toolbar, text="保存报告", command=self._save_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(report_toolbar, text="清空", command=self._clear_report).pack(side=tk.LEFT, padx=2)
        
        # 报告文本区域
        self.report_text = scrolledtext.ScrolledText(
            self.report_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 10)
        )
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_export_tab(self):
        """创建导出标签页"""
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="导出")
        
        # 导出选项
        options_frame = ttk.LabelFrame(self.export_frame, text="导出选项", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 导出格式
        ttk.Label(options_frame, text="导出格式:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.export_format = tk.StringVar(value="CSV")
        format_combo = ttk.Combobox(options_frame, textvariable=self.export_format, 
                                   values=["CSV", "JSON", "TXT"], state="readonly")
        format_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 导出内容选项
        self.export_options = {}
        options = [
            ("include_success", "包含成功结果", True),
            ("include_failed", "包含失败结果", True),
            ("include_details", "包含详细信息", True),
            ("include_raw_text", "包含原始OCR文本", False),
            ("include_warnings", "包含警告信息", True)
        ]
        
        for i, (key, text, default) in enumerate(options):
            self.export_options[key] = tk.BooleanVar(value=default)
            ttk.Checkbutton(options_frame, text=text, variable=self.export_options[key]).grid(
                row=i+1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2
            )
        
        # 导出按钮
        export_buttons_frame = ttk.Frame(self.export_frame)
        export_buttons_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(export_buttons_frame, text="导出结果", command=self._export_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_buttons_frame, text="导出统计", command=self._export_statistics).pack(side=tk.LEFT, padx=5)
    
    def show_batch_result(self, batch_result: BatchResult):
        """显示批量处理结果
        
        Args:
            batch_result: 批量处理结果
        """
        self.current_batch_result = batch_result
        self.current_results = batch_result.results
        
        # 更新摘要
        self._update_summary()
        
        # 更新详细结果
        self._update_details()
        
        # 生成报告
        self._generate_report()
        
        logger.info(f"显示批量结果: {len(batch_result.results)} 个结果")
    
    def show_single_result(self, result: RecognitionResult):
        """显示单个识别结果
        
        Args:
            result: 识别结果
        """
        self.current_results = [result]
        self.current_batch_result = None
        
        # 更新详细结果
        self._update_details()
        
        logger.info(f"显示单个结果: {result.image_path}")
    
    def _update_summary(self):
        """更新摘要信息"""
        if not self.current_batch_result:
            return
        
        batch = self.current_batch_result
        
        # 更新统计标签
        self.stats_labels['total_files'].config(text=str(batch.total_files))
        self.stats_labels['processed_files'].config(text=str(batch.total_processed))
        self.stats_labels['success_count'].config(text=str(batch.successful_recognitions))
        self.stats_labels['failed_count'].config(text=str(batch.failed_recognitions))
        self.stats_labels['success_rate'].config(text=f"{batch.success_rate:.1%}")
        self.stats_labels['processing_time'].config(text=f"{batch.processing_time:.2f}秒")
        
        # 更新日期统计
        self._update_date_statistics()
    
    def _update_date_statistics(self):
        """更新日期统计"""
        # 清空现有数据
        self.date_tree.delete(*self.date_tree.get_children())
        
        if not self.current_results:
            return
        
        # 统计日期出现次数
        date_stats = {}
        for result in self.current_results:
            if result.success and result.dates_found:
                for date in result.dates_found:
                    if date not in date_stats:
                        date_stats[date] = {'count': 0, 'files': set()}
                    date_stats[date]['count'] += 1
                    date_stats[date]['files'].add(result.image_path)
        
        # 添加到树形视图
        for date, stats in sorted(date_stats.items()):
            self.date_tree.insert('', tk.END, 
                                text=date,
                                values=(stats['count'], len(stats['files'])))
    
    def _update_details(self):
        """更新详细结果"""
        # 清空现有数据
        self.result_tree.delete(*self.result_tree.get_children())
        
        if not self.current_results:
            return
        
        # 添加结果到树形视图
        for result in self.current_results:
            file_name = result.image_path.split('/')[-1] if '/' in result.image_path else result.image_path.split('\\')[-1]
            status = "成功" if result.success else "失败"
            dates = ", ".join(result.dates_found) if result.dates_found else "--"
            confidence = f"{result.confidence:.2f}" if result.confidence > 0 else "--"
            processing_time = f"{result.processing_time:.2f}s"
            warning = result.warning_message or "--"
            
            # 根据状态设置颜色标签
            tags = []
            if result.success:
                if result.get_warning_level() in ['medium', 'high']:
                    tags.append('warning')
                else:
                    tags.append('success')
            else:
                tags.append('failed')
            
            self.result_tree.insert('', tk.END,
                                  text=result.image_path,
                                  values=(file_name, status, dates, confidence, processing_time, warning),
                                  tags=tags)
        
        # 配置标签颜色
        self.result_tree.tag_configure('success', foreground='green')
        self.result_tree.tag_configure('warning', foreground='orange')
        self.result_tree.tag_configure('failed', foreground='red')
    
    def _show_all_results(self):
        """显示所有结果"""
        self._update_details()
    
    def _show_success_only(self):
        """仅显示成功结果"""
        self._filter_results(lambda r: r.success)
    
    def _show_failed_only(self):
        """仅显示失败结果"""
        self._filter_results(lambda r: not r.success)
    
    def _show_warnings_only(self):
        """仅显示有警告的结果"""
        self._filter_results(lambda r: r.warning_message is not None)
    
    def _filter_results(self, filter_func):
        """过滤结果显示
        
        Args:
            filter_func: 过滤函数
        """
        # 清空现有数据
        self.result_tree.delete(*self.result_tree.get_children())
        
        if not self.current_results:
            return
        
        # 过滤并显示结果
        filtered_results = [r for r in self.current_results if filter_func(r)]
        
        for result in filtered_results:
            file_name = result.image_path.split('/')[-1] if '/' in result.image_path else result.image_path.split('\\')[-1]
            status = "成功" if result.success else "失败"
            dates = ", ".join(result.dates_found) if result.dates_found else "--"
            confidence = f"{result.confidence:.2f}" if result.confidence > 0 else "--"
            processing_time = f"{result.processing_time:.2f}s"
            warning = result.warning_message or "--"
            
            tags = []
            if result.success:
                if result.get_warning_level() in ['medium', 'high']:
                    tags.append('warning')
                else:
                    tags.append('success')
            else:
                tags.append('failed')
            
            self.result_tree.insert('', tk.END,
                                  text=result.image_path,
                                  values=(file_name, status, dates, confidence, processing_time, warning),
                                  tags=tags)
    
    def _generate_report(self):
        """生成报告"""
        if self.current_batch_result:
            report = self.current_batch_result.generate_report()
        else:
            report = "无批量处理结果"
        
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, report)
    
    def _save_report(self):
        """保存报告"""
        if not hasattr(self, 'file_dialog_manager'):
            # 创建文件对话框管理器（需要父窗口）
            parent_window = self.winfo_toplevel()
            self.file_dialog_manager = create_file_dialog_manager(parent_window)
        
        file_path = self.file_dialog_manager.save_file(
            title="保存报告",
            default_extension=".txt",
            file_types=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.report_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"报告已保存到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存报告失败: {e}")
    
    def _clear_report(self):
        """清空报告"""
        self.report_text.delete(1.0, tk.END)
    
    def _export_results(self):
        """导出结果"""
        if not self.current_results:
            messagebox.showwarning("警告", "没有结果可以导出")
            return
        
        # 实现导出功能
        messagebox.showinfo("信息", "导出功能正在开发中...")
    
    def _export_statistics(self):
        """导出统计信息"""
        if not self.current_batch_result:
            messagebox.showwarning("警告", "没有统计信息可以导出")
            return
        
        # 实现导出功能
        messagebox.showinfo("信息", "导出功能正在开发中...")
    
    def _on_result_select(self, event):
        """结果选择事件"""
        selection = self.result_tree.selection()
        if selection:
            item = self.result_tree.item(selection[0])
            file_path = item['text']
            # 可以在这里显示更详细的信息
    
    def _on_result_double_click(self, event):
        """结果双击事件"""
        selection = self.result_tree.selection()
        if selection:
            item = self.result_tree.item(selection[0])
            file_path = item['text']
            
            # 查找对应的结果
            result = None
            for r in self.current_results:
                if r.image_path == file_path:
                    result = r
                    break
            
            if result:
                self._show_result_details(result)
    
    def _show_result_details(self, result: RecognitionResult):
        """显示结果详细信息
        
        Args:
            result: 识别结果
        """
        details = f"""文件: {result.image_path}
状态: {'成功' if result.success else '失败'}
识别到的日期: {', '.join(result.dates_found) if result.dates_found else '无'}
置信度: {result.confidence:.3f}
处理时间: {result.processing_time:.3f}秒
图像尺寸: {result.image_size[0]}x{result.image_size[1]}
警告信息: {result.warning_message or '无'}

原始OCR文本:
{chr(10).join(result.raw_text) if result.raw_text else '无'}
"""
        messagebox.showinfo("详细信息", details)
    
    def clear(self):
        """清空显示"""
        self.current_batch_result = None
        self.current_results = []
        
        # 清空所有显示
        for label in self.stats_labels.values():
            label.config(text="--")
        
        self.date_tree.delete(*self.date_tree.get_children())
        self.result_tree.delete(*self.result_tree.get_children())
        self.report_text.delete(1.0, tk.END)
    
    def refresh(self):
        """刷新显示"""
        if self.current_batch_result:
            self.show_batch_result(self.current_batch_result)
        elif self.current_results:
            self._update_details()


# 工厂函数
def create_result_display_widget(parent) -> ResultDisplayWidget:
    """创建结果显示组件实例
    
    Args:
        parent: 父组件
        
    Returns:
        结果显示组件实例
    """
    return ResultDisplayWidget(parent)
