#!/usr/bin/env python3
"""
v1主程序OCR引擎诊断脚本
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def diagnose_v1_ocr_integration():
    """诊断v1主程序的OCR引擎集成"""
    print("🔍 v1主程序OCR引擎集成诊断")
    print("=" * 60)
    
    try:
        print("1. 测试date_recognizer的OCR引擎...")
        from core.date_recognizer import create_date_recognizer
        
        date_recognizer = create_date_recognizer()
        print("✅ date_recognizer创建成功")
        
        # 检查OCR引擎类型
        ocr_engine = date_recognizer.ocr_engine
        engine_info = ocr_engine.get_engine_info()
        
        print(f"OCR引擎类型: {engine_info.get('engine_type', 'unknown')}")
        print(f"OCR引擎版本: {engine_info.get('version', 'unknown')}")
        
        if 'OptimizedPaddleOCR' in engine_info.get('engine_type', ''):
            print("✅ 使用优化版OCR引擎")
        else:
            print("⚠️ 使用标准版OCR引擎")
        
        print("\n2. 测试单张图片识别...")
        test_image = project_root / "test_image" / "2012.11.26.jpg"
        
        if not test_image.exists():
            print("❌ 测试图片不存在")
            return False
        
        print(f"测试图片: {test_image.name}")
        
        start_time = time.time()
        try:
            # 使用date_recognizer的recognize_single方法
            result = date_recognizer.recognize_single(str(test_image))
            processing_time = time.time() - start_time
            
            print(f"✅ 识别成功 ({processing_time:.2f}秒)")
            print(f"识别到文本: {len(result.ocr_results)} 个")
            print(f"识别到日期: {len(result.dates_found)} 个")

            # 显示识别结果
            if result.ocr_results:
                print("文本结果:")
                for i, text in enumerate(result.ocr_results[:5]):
                    print(f"   {i+1}. '{text.text}' (置信度: {text.confidence:.2f})")
            
            if result.dates_found:
                print("日期结果:")
                for i, date in enumerate(result.dates_found):
                    print(f"   {i+1}. {date.date_string} (置信度: {date.confidence:.2f})")
            
            return len(result.dates_found) > 0
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ 识别失败: {e} ({processing_time:.2f}秒)")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def diagnose_batch_processor():
    """诊断批量处理器"""
    print("\n" + "=" * 60)
    print("🔍 批量处理器诊断")
    print("=" * 60)
    
    try:
        print("1. 测试批量处理器创建...")
        from v1.handlers.batch_processor import create_batch_processor
        
        batch_processor = create_batch_processor()
        print("✅ 批量处理器创建成功")
        
        print("2. 检查批量处理器的date_recognizer...")
        date_recognizer = batch_processor.date_recognizer
        ocr_engine = date_recognizer.ocr_engine
        engine_info = ocr_engine.get_engine_info()
        
        print(f"批量处理器使用的OCR引擎: {engine_info.get('engine_type', 'unknown')}")
        
        print("3. 测试批量处理单个文件...")
        test_image = project_root / "test_image" / "2012.11.26.jpg"
        
        if test_image.exists():
            start_time = time.time()
            try:
                # 使用批量处理器的内部方法
                result = batch_processor._process_single_file(str(test_image))
                processing_time = time.time() - start_time
                
                print(f"✅ 批量处理成功 ({processing_time:.2f}秒)")
                print(f"处理状态: {'成功' if result.success else '失败'}")

                if result.result:
                    rec_result = result.result
                    print(f"识别到文本: {len(rec_result.ocr_results)} 个")
                    print(f"识别到日期: {len(rec_result.dates_found)} 个")

                return result.success
                
            except Exception as e:
                processing_time = time.time() - start_time
                print(f"❌ 批量处理失败: {e} ({processing_time:.2f}秒)")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("⚠️ 测试图片不存在，跳过测试")
            return True
        
    except Exception as e:
        print(f"❌ 批量处理器诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_ocr_comparison():
    """对比直接OCR和v1流程的结果"""
    print("\n" + "=" * 60)
    print("🔍 直接OCR vs v1流程对比")
    print("=" * 60)
    
    try:
        test_image = project_root / "test_image" / "2012.11.26.jpg"
        
        if not test_image.exists():
            print("❌ 测试图片不存在")
            return False
        
        print("1. 直接使用优化OCR引擎...")
        from core.optimized_paddleocr_engine import OptimizedPaddleOCREngine
        
        ocr_engine = OptimizedPaddleOCREngine()
        
        start_time = time.time()
        direct_result = ocr_engine.ocr(str(test_image))
        direct_time = time.time() - start_time
        
        direct_text_count = len(direct_result[0]) if direct_result and direct_result[0] else 0
        print(f"直接OCR: {direct_text_count} 个文本 ({direct_time:.2f}秒)")
        
        print("2. 通过v1流程...")
        from core.date_recognizer import create_date_recognizer
        
        date_recognizer = create_date_recognizer()
        
        start_time = time.time()
        v1_result = date_recognizer.recognize_single(str(test_image))
        v1_time = time.time() - start_time
        
        v1_text_count = len(v1_result.ocr_results)
        v1_date_count = len(v1_result.dates_found)
        print(f"v1流程: {v1_text_count} 个文本, {v1_date_count} 个日期 ({v1_time:.2f}秒)")

        print("\n3. 结果对比:")
        print(f"直接OCR文本数: {direct_text_count}")
        print(f"v1流程文本数: {v1_text_count}")
        print(f"v1流程日期数: {v1_date_count}")
        print(f"处理时间对比: 直接{direct_time:.2f}s vs v1流程{v1_time:.2f}s")

        # 显示详细结果
        if direct_result and direct_result[0]:
            print("\n直接OCR结果:")
            for i, (bbox, (text, confidence)) in enumerate(direct_result[0][:3]):
                print(f"   {i+1}. '{text}' (置信度: {confidence:.2f})")

        if v1_result.ocr_results:
            print("\nv1流程文本结果:")
            for i, text in enumerate(v1_result.ocr_results[:3]):
                print(f"   {i+1}. '{text.text}' (置信度: {text.confidence:.2f})")
        
        if v1_result.dates_found:
            print("\nv1流程日期结果:")
            for i, date in enumerate(v1_result.dates_found):
                print(f"   {i+1}. {date.date_string} (置信度: {date.confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 对比测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主诊断函数"""
    print("🔬 v1主程序OCR引擎完整诊断")
    
    # 诊断v1 OCR集成
    v1_ocr_ok = diagnose_v1_ocr_integration()
    
    # 诊断批量处理器
    batch_ok = diagnose_batch_processor()
    
    # 对比测试
    comparison_ok = test_direct_ocr_comparison()
    
    print("\n" + "=" * 60)
    print("📋 v1主程序诊断总结")
    print("=" * 60)
    
    print(f"v1 OCR集成: {'✅ 正常' if v1_ocr_ok else '❌ 异常'}")
    print(f"批量处理器: {'✅ 正常' if batch_ok else '❌ 异常'}")
    print(f"对比测试: {'✅ 正常' if comparison_ok else '❌ 异常'}")
    
    if v1_ocr_ok and batch_ok and comparison_ok:
        print("\n🎉 v1主程序OCR集成正常")
        print("如果识别率仍然很低，可能的原因:")
        print("1. 图片预处理影响了识别效果")
        print("2. 日期解析器过滤了一些结果")
        print("3. 缓存中存储的是旧的低质量结果")
        print("\n建议:")
        print("- 清理缓存数据库")
        print("- 检查图片预处理设置")
        print("- 调整日期解析器的过滤条件")
    else:
        print("\n⚠️ 发现问题，需要进一步修复")
        if not v1_ocr_ok:
            print("- v1 OCR集成有问题")
        if not batch_ok:
            print("- 批量处理器有问题")
        if not comparison_ok:
            print("- 对比测试有问题")

if __name__ == "__main__":
    main()
