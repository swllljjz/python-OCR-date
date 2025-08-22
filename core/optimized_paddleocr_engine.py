"""
优化的PaddleOCR引擎 - 提升速度和准确率
集成智能图像预处理和多策略处理
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
from pathlib import Path
import time
import threading
import queue
import tempfile
import os
from .smart_image_processor import SmartImageProcessor
from .smart_roi_detector import SmartROIDetector
from .cache_manager import CacheManager

class OptimizedPaddleOCREngine:
    """优化的PaddleOCR引擎 - 专注速度和准确率

    集成功能:
    - 智能图像预处理
    - 动态超时策略
    - 多策略处理机制
    """

    def __init__(self):
        """初始化优化的PaddleOCR引擎"""
        print("正在初始化增强版PaddleOCR引擎...")

        # 初始化智能图像处理器和ROI检测器
        self.image_processor = SmartImageProcessor()
        self.roi_detector = SmartROIDetector()

        # 初始化缓存管理器
        try:
            self.cache_manager = CacheManager()
            print("✅ 缓存管理器已启用")
        except Exception as e:
            print(f"⚠️ 缓存管理器初始化失败: {e}")
            self.cache_manager = None

        # 性能统计
        self.stats = {
            'total_processed': 0,
            'success_count': 0,
            'preprocessing_time': 0,
            'ocr_time': 0,
            'roi_time': 0,
            'roi_regions_detected': 0,
            'strategy_usage': {'standard': 0, 'enhanced': 0, 'aggressive': 0}
        }

        try:
            # 尝试导入PaddleOCR
            from paddleocr import PaddleOCR

            # 创建PaddleOCR实例，优化参数以提升速度
            self.reader = PaddleOCR(
                use_angle_cls=True,       # 启用文字方向分类
                lang='ch',                # 中文识别
            )
            print("增强版PaddleOCR引擎初始化完成")

        except ImportError:
            print("PaddleOCR未安装，请运行: pip install paddlepaddle paddleocr")
            raise Exception("PaddleOCR未安装")
        except Exception as e:
            print(f"PaddleOCR初始化失败: {e}")
            raise

    def _calculate_dynamic_timeout(self, image_input) -> int:
        """根据图片大小计算动态超时时间

        Args:
            image_input: 可以是图片路径(str)或图片尺寸元组(width, height)
        """
        try:
            if isinstance(image_input, str):
                # 图片路径
                img = cv2.imread(image_input)
                if img is None:
                    return 20  # 默认超时
                height, width = img.shape[:2]
            elif isinstance(image_input, (tuple, list)) and len(image_input) == 2:
                # 图片尺寸元组
                width, height = image_input
            else:
                print(f"无效的图片输入类型: {type(image_input)}")
                return 20  # 默认超时

            pixels = width * height

            # 基于像素数量的动态超时策略
            if pixels > 2000000:    # >200万像素
                timeout = 35
            elif pixels > 1000000:  # >100万像素
                timeout = 25
            elif pixels > 500000:   # >50万像素
                timeout = 20
            else:
                timeout = 15

            print(f"图片尺寸: {width}x{height} ({pixels:,}像素) → 超时设置: {timeout}秒")
            return timeout

        except Exception as e:
            print(f"计算动态超时失败: {e}")
            return 20  # 默认超时

    def _process_with_smart_preprocessing(self, image_path: str, strategy: str = "standard") -> Tuple[str, bool]:
        """使用智能预处理处理图片

        Args:
            image_path: 输入图片路径
            strategy: 处理策略 ('standard', 'enhanced', 'aggressive')

        Returns:
            (处理后图片路径, 是否为临时文件)
        """
        try:
            start_time = time.time()
            temp_files = []

            if strategy == "standard":
                # 标准预处理：仅尺寸调整
                processed_path, is_temp = self.image_processor.auto_resize(image_path)
                self.stats['strategy_usage']['standard'] += 1

            elif strategy == "enhanced":
                # 增强预处理：尺寸调整 + 标准增强
                resized_path, is_temp1 = self.image_processor.auto_resize(image_path)
                if is_temp1:
                    temp_files.append(resized_path)

                processed_path, is_temp2 = self.image_processor.enhance_for_ocr(resized_path, "standard")
                is_temp = is_temp2  # 最终文件是否为临时文件
                self.stats['strategy_usage']['enhanced'] += 1

            elif strategy == "aggressive":
                # 激进预处理：尺寸调整 + 激进增强
                resized_path, is_temp1 = self.image_processor.auto_resize(image_path)
                if is_temp1:
                    temp_files.append(resized_path)

                processed_path, is_temp2 = self.image_processor.enhance_for_ocr(resized_path, "aggressive")
                is_temp = is_temp2  # 最终文件是否为临时文件
                self.stats['strategy_usage']['aggressive'] += 1

            else:
                processed_path, is_temp = image_path, False

            processing_time = time.time() - start_time
            self.stats['preprocessing_time'] += processing_time

            print(f"预处理完成 ({strategy}策略): 耗时 {processing_time:.2f}秒")
            return processed_path, is_temp

        except Exception as e:
            print(f"预处理失败 ({strategy}策略): {e}")
            return image_path, False

    def _should_use_roi(self, image_path: str) -> bool:
        """判断是否应该使用ROI检测"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False

            height, width = img.shape[:2]
            pixels = width * height

            # 小图片跳过ROI检测
            if pixels < 250000:  # 小于500x500像素
                print(f"图片较小 ({width}x{height})，跳过ROI检测")
                return False

            # 超大图片使用ROI检测
            if pixels > 1000000:  # 大于1000x1000像素
                print(f"图片较大 ({width}x{height})，使用ROI检测")
                return True

            # 中等图片根据宽高比判断
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 3:  # 长条形图片，可能有多个文本区域
                print(f"图片为长条形 ({width}x{height})，使用ROI检测")
                return True

            print(f"图片中等大小 ({width}x{height})，跳过ROI检测")
            return False

        except Exception as e:
            print(f"判断ROI使用失败: {e}")
            return False

    def _process_with_roi_detection(self, image_path: str, use_roi: bool = True) -> Tuple[List[str], bool]:
        """使用ROI检测优化处理速度

        Args:
            image_path: 输入图片路径
            use_roi: 是否使用ROI检测

        Returns:
            (处理后图片路径列表, 是否使用了ROI)
        """
        # 智能判断是否使用ROI
        if not use_roi or not self._should_use_roi(image_path):
            return [image_path], False

        try:
            start_time = time.time()

            # 检测文本区域
            cropped_paths = self.roi_detector.crop_text_regions(image_path, padding=30)

            roi_time = time.time() - start_time
            self.stats['roi_time'] += roi_time

            # 检查ROI检测效果
            if len(cropped_paths) > 1 and len(cropped_paths) <= 15:  # 合理的区域数量
                # 预估处理时间
                estimated_time = len(cropped_paths) * 8  # 每个区域预估8秒
                if estimated_time <= 60:  # 预估时间不超过60秒
                    self.stats['roi_regions_detected'] += len(cropped_paths)
                    print(f"ROI检测完成: 发现 {len(cropped_paths)} 个文本区域 (耗时: {roi_time:.2f}秒, 预估处理: {estimated_time}秒)")
                    return cropped_paths, True
                else:
                    print(f"ROI检测: 区域过多({len(cropped_paths)}个)，预估时间过长({estimated_time}秒)，使用原图")
                    return [image_path], False
            else:
                print(f"ROI检测: 区域数量不合适({len(cropped_paths)}个)，使用原图 (耗时: {roi_time:.2f}秒)")
                return [image_path], False

        except Exception as e:
            print(f"ROI检测失败: {e}")
            return [image_path], False

    def _smart_resize_image(self, image_path: str) -> Tuple[str, Tuple[int, int]]:
        """智能缩放图片以提升处理速度"""
        try:
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                return image_path, (0, 0)
            
            height, width = img.shape[:2]
            original_size = (width, height)
            
            # 如果图片尺寸合适，直接返回
            max_size = 1280
            if width <= max_size and height <= max_size:
                return image_path, original_size
            
            # 计算缩放比例
            scale = min(max_size / width, max_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 缩放图片
            resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # 保存到临时文件
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(temp_path, resized_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            print(f"图片缩放: {width}x{height} → {new_width}x{new_height} (缩放比例: {scale:.2f})")
            return temp_path, original_size
            
        except Exception as e:
            print(f"图片缩放失败: {e}")
            return image_path, (0, 0)
    
    def _enhance_image_for_ocr(self, image_path: str) -> str:
        """针对OCR优化图片质量"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return image_path
            
            # 转换为灰度图
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            
            # 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 轻微去噪
            denoised = cv2.medianBlur(enhanced, 3)
            
            # 自适应二值化
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 保存增强后的图片
            temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(temp_path, binary)
            
            return temp_path
            
        except Exception as e:
            print(f"图片增强失败: {e}")
            return image_path
    

    
    def _ocr_worker(self, image_path: str, result_queue: queue.Queue):
        """OCR工作线程"""
        try:
            results = self.reader.predict(image_path)
            result_queue.put(('success', results))
        except Exception as e:
            result_queue.put(('error', str(e)))

    def _execute_ocr_with_timeout(self, image_path: str, timeout_seconds: int):
        """执行带超时的OCR识别"""
        try:
            result_queue = queue.Queue()
            worker_thread = threading.Thread(
                target=self._ocr_worker,
                args=(image_path, result_queue)
            )
            worker_thread.daemon = True
            worker_thread.start()

            try:
                status, results = result_queue.get(timeout=timeout_seconds)

                if status == 'success':
                    return results
                else:
                    print(f"OCR执行错误: {results}")
                    return None

            except queue.Empty:
                print(f"OCR执行超时 ({timeout_seconds}秒)")
                return None

        except Exception as e:
            print(f"OCR执行异常: {e}")
            return None

    def _process_roi_regions(self, roi_paths: List[str], timeout_seconds: int,
                           temp_files: List[str], start_time: float):
        """处理ROI检测到的多个区域"""
        all_results = []

        for i, roi_path in enumerate(roi_paths):
            print(f"处理ROI区域 {i+1}/{len(roi_paths)}: {roi_path}")

            # 对每个ROI区域使用标准策略处理
            processed_path, is_temp = self._process_with_smart_preprocessing(roi_path, "standard")
            if is_temp:
                temp_files.append(processed_path)

            # 执行OCR
            result = self._execute_ocr_with_timeout(processed_path, timeout_seconds)

            if result and result[0]:
                formatted_results = self._format_results(result)
                if formatted_results:
                    all_results.extend(formatted_results)
                    print(f"✅ ROI区域 {i+1} 成功: 找到 {len(formatted_results)} 个文本")
                else:
                    print(f"❌ ROI区域 {i+1} 无有效文本")
            else:
                print(f"❌ ROI区域 {i+1} 识别失败")

        if all_results:
            processing_time = time.time() - start_time
            self.stats['success_count'] += 1
            print(f"✅ ROI处理成功: 总共找到 {len(all_results)} 个文本 (总耗时: {processing_time:.2f}秒)")
            return [all_results]
        else:
            print("❌ 所有ROI区域都失败，尝试传统方法...")
            # 回退到传统方法
            return self._process_with_strategies(roi_paths[0], ["standard", "enhanced"],
                                               timeout_seconds, temp_files, start_time)

    def _process_with_strategies(self, image_path: str, strategies: List[str],
                               timeout_seconds: int, temp_files: List[str], start_time: float):
        """使用多策略处理单个图片"""
        for i, strategy in enumerate(strategies):
            strategy_start = time.time()

            # 1. 智能预处理
            processed_path, is_temp = self._process_with_smart_preprocessing(image_path, strategy)
            if is_temp:
                temp_files.append(processed_path)

            # 2. 计算当前策略的超时时间
            if strategy == "standard":
                current_timeout = timeout_seconds
            elif strategy == "enhanced":
                current_timeout = int(timeout_seconds * 1.2)  # 增加20%
            else:  # aggressive
                current_timeout = int(timeout_seconds * 1.5)  # 增加50%

            print(f"尝试{strategy}策略 (超时: {current_timeout}秒)...")

            # 3. 执行OCR识别
            result = self._execute_ocr_with_timeout(processed_path, current_timeout)

            if result and result[0]:  # 识别成功
                formatted_results = self._format_results(result)
                if formatted_results:
                    processing_time = time.time() - start_time
                    strategy_time = time.time() - strategy_start

                    self.stats['success_count'] += 1
                    self.stats['ocr_time'] += strategy_time

                    print(f"✅ {strategy}策略成功: 找到 {len(formatted_results)} 个文本 (策略耗时: {strategy_time:.2f}秒, 总耗时: {processing_time:.2f}秒)")
                    return [formatted_results]

            strategy_time = time.time() - strategy_start
            print(f"❌ {strategy}策略失败 (耗时: {strategy_time:.2f}秒)")

            # 如果不是最后一个策略，继续尝试
            if i < len(strategies) - 1:
                print(f"尝试下一个策略...")

        # 所有策略都失败
        processing_time = time.time() - start_time
        print(f"❌ 所有策略都失败 (总耗时: {processing_time:.2f}秒)")
        return [[]]
    
    def ocr(self, image, timeout_seconds=None):
        """增强版多策略OCR识别

        实施三级处理策略:
        1. 标准处理: 快速预处理 + 标准超时
        2. 增强处理: 图像增强 + 中等超时
        3. 激进处理: 激进增强 + 长超时
        """
        start_time = time.time()
        self.stats['total_processed'] += 1

        # 处理输入
        if isinstance(image, str):
            image_path = image
        else:
            # 图像数组，保存为临时文件
            temp_fd, image_path = tempfile.mkstemp(suffix='.jpg')
            os.close(temp_fd)
            cv2.imwrite(image_path, image)

        # 检查缓存
        if self.cache_manager and isinstance(image, str):  # 只对文件路径启用缓存
            cached_result = self.cache_manager.get_cached_result(image_path)
            if cached_result:
                processing_time = time.time() - start_time
                print(f"⚡ 缓存命中，跳过OCR处理 (缓存查询耗时: {processing_time:.3f}秒)")
                return cached_result['ocr_results']

        # 动态计算基础超时时间
        base_timeout = self._calculate_dynamic_timeout(image_path)
        if timeout_seconds is None:
            timeout_seconds = base_timeout

        temp_files = []
        strategies = ["standard", "enhanced", "aggressive"]

        print(f"开始多策略OCR识别 (基础超时: {timeout_seconds}秒)...")

        try:
            # 首先尝试ROI检测优化
            roi_paths, used_roi = self._process_with_roi_detection(image_path, use_roi=True)

            if used_roi and len(roi_paths) > 1:
                # 使用ROI检测结果进行并行处理
                result = self._process_roi_regions(roi_paths, timeout_seconds, temp_files, start_time)
            else:
                # 使用传统的多策略处理
                result = self._process_with_strategies(image_path, strategies, timeout_seconds, temp_files, start_time)

            # 保存成功结果到缓存
            if result and result[0] and self.cache_manager and isinstance(image, str):
                processing_time = time.time() - start_time
                strategy_used = "roi" if used_roi else "traditional"
                self.cache_manager.save_result(image_path, result, processing_time, strategy_used)

            return result
            
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            # 如果原始输入不是文件路径，清理临时文件
            if not isinstance(image, str):
                try:
                    os.unlink(image_path)
                except:
                    pass
    
    def _format_results(self, results):
        """格式化OCR结果"""
        formatted_results = []
        if results and len(results) > 0:
            ocr_result = results[0]
            
            if isinstance(ocr_result, dict) and 'rec_texts' in ocr_result:
                texts = ocr_result['rec_texts']
                scores = ocr_result.get('rec_scores', [])
                polys = ocr_result.get('rec_polys', [])
                
                for i in range(len(texts)):
                    try:
                        text = str(texts[i]).strip()
                        confidence = float(scores[i]) if i < len(scores) else 0.5
                        
                        # 降低置信度阈值以提高召回率
                        if confidence > 0.2 and len(text) > 0:
                            bbox = polys[i] if i < len(polys) else [[0,0],[0,0],[0,0],[0,0]]
                            if hasattr(bbox, 'tolist'):
                                bbox = bbox.tolist()
                            formatted_results.append([bbox, (text, confidence)])
                    except Exception as e:
                        continue
        
        return formatted_results

    def get_stats(self):
        """获取性能统计信息"""
        total = self.stats['total_processed']
        success = self.stats['success_count']

        stats = {
            'total_processed': total,
            'success_count': success,
            'success_rate': f"{(success/total*100):.1f}%" if total > 0 else "0%",
            'avg_preprocessing_time': f"{(self.stats['preprocessing_time']/total):.2f}s" if total > 0 else "0s",
            'avg_ocr_time': f"{(self.stats['ocr_time']/success):.2f}s" if success > 0 else "0s",
            'avg_roi_time': f"{(self.stats['roi_time']/total):.2f}s" if total > 0 else "0s",
            'roi_regions_detected': self.stats['roi_regions_detected'],
            'avg_roi_regions': f"{(self.stats['roi_regions_detected']/total):.1f}" if total > 0 else "0",
            'strategy_usage': self.stats['strategy_usage'].copy()
        }

        # 添加缓存统计
        if self.cache_manager:
            cache_stats = self.cache_manager.get_cache_stats()
            stats.update({
                'cache_enabled': True,
                'cache_hit_rate': cache_stats['hit_rate'],
                'cache_total_requests': cache_stats['total_requests'],
                'cache_hits': cache_stats['cache_hits'],
                'cache_count': cache_stats['cache_count'],
                'cache_size': cache_stats['cache_size_mb']
            })
        else:
            stats['cache_enabled'] = False

        return stats

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_processed': 0,
            'success_count': 0,
            'preprocessing_time': 0,
            'ocr_time': 0,
            'roi_time': 0,
            'roi_regions_detected': 0,
            'strategy_usage': {'standard': 0, 'enhanced': 0, 'aggressive': 0}
        }
