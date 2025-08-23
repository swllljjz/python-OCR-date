#!/usr/bin/env python3
"""
OCR问题诊断脚本
"""

import sys
import time
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def diagnose_cache_issues():
    """诊断缓存问题"""
    print("🔍 缓存问题诊断")
    print("=" * 50)
    
    try:
        from core.cache_manager import CacheManager
        
        cache = CacheManager()
        print("✅ 缓存管理器创建成功")
        
        # 检查缓存统计
        stats = cache.get_stats()
        print(f"\n📊 缓存统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 检查缓存数据库
        cache_db_path = project_root / "cache" / "ocr_cache.db"
        if cache_db_path.exists():
            print(f"\n✅ 缓存数据库存在: {cache_db_path}")
            print(f"数据库大小: {cache_db_path.stat().st_size / 1024:.2f} KB")
        else:
            print(f"\n❌ 缓存数据库不存在: {cache_db_path}")
        
        # 测试缓存查询
        test_image = project_root / "test_image" / "2012.11.26.jpg"
        if test_image.exists():
            print(f"\n🔍 测试缓存查询: {test_image.name}")
            
            # 计算文件哈希
            file_hash = cache._calculate_file_hash(str(test_image))
            print(f"文件哈希: {file_hash}")
            
            # 查询缓存
            cached_result = cache.get_result(str(test_image))
            if cached_result:
                print("✅ 缓存命中")
                print(f"缓存结果: {len(cached_result)} 个文本")
            else:
                print("❌ 缓存未命中")
        
        return True
        
    except Exception as e:
        print(f"❌ 缓存诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def diagnose_ocr_engine():
    """诊断OCR引擎问题"""
    print("\n" + "=" * 50)
    print("🔍 OCR引擎问题诊断")
    print("=" * 50)
    
    try:
        from core.optimized_paddleocr_engine import OptimizedPaddleOCREngine
        
        print("1. 创建OCR引擎...")
        ocr_engine = OptimizedPaddleOCREngine()
        
        print("2. 检查OCR实例...")
        if hasattr(ocr_engine, 'reader') and ocr_engine.reader is not None:
            print("✅ PaddleOCR实例存在")
            
            if hasattr(ocr_engine.reader, 'ocr'):
                print("✅ PaddleOCR.ocr方法可用")
            else:
                print("❌ PaddleOCR.ocr方法不存在")
                return False
        else:
            print("❌ PaddleOCR实例不存在")
            return False
        
        print("3. 测试单张图片OCR...")
        test_image = project_root / "test_image" / "2012.11.26.jpg"
        
        if not test_image.exists():
            print("❌ 测试图片不存在")
            return False
        
        print(f"测试图片: {test_image.name}")
        
        # 直接调用PaddleOCR
        print("   直接调用PaddleOCR...")
        start_time = time.time()
        try:
            raw_result = ocr_engine.reader.ocr(str(test_image))
            direct_time = time.time() - start_time
            print(f"   ✅ 直接调用成功 ({direct_time:.2f}秒)")
            
            if raw_result and len(raw_result) > 0 and raw_result[0]:
                print(f"   识别到 {len(raw_result[0])} 个文本")
                for i, line in enumerate(raw_result[0][:3]):
                    bbox, (text, confidence) = line
                    print(f"     {i+1}. '{text}' (置信度: {confidence:.2f})")
            else:
                print("   ⚠️ 未识别到文本")
        except Exception as e:
            direct_time = time.time() - start_time
            print(f"   ❌ 直接调用失败: {e} ({direct_time:.2f}秒)")
            return False
        
        # 通过优化引擎调用
        print("   通过优化引擎调用...")
        start_time = time.time()
        try:
            engine_result = ocr_engine.ocr(str(test_image))
            engine_time = time.time() - start_time
            print(f"   ✅ 引擎调用成功 ({engine_time:.2f}秒)")
            
            if engine_result and len(engine_result) > 0 and engine_result[0]:
                print(f"   识别到 {len(engine_result[0])} 个文本")
            else:
                print("   ⚠️ 未识别到文本")
        except Exception as e:
            engine_time = time.time() - start_time
            print(f"   ❌ 引擎调用失败: {e} ({engine_time:.2f}秒)")
            import traceback
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ OCR引擎诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def diagnose_main_program_integration():
    """诊断主程序集成问题"""
    print("\n" + "=" * 50)
    print("🔍 主程序集成诊断")
    print("=" * 50)
    
    try:
        print("1. 测试主程序OCR引擎获取...")
        from core.ocr_engine import get_ocr_engine
        
        main_ocr_engine = get_ocr_engine()
        engine_info = main_ocr_engine.get_engine_info()
        print(f"主程序使用的引擎: {engine_info.get('engine_type', 'unknown')}")
        
        print("2. 测试主程序识别接口...")
        test_image = project_root / "test_image" / "2012.11.26.jpg"
        
        if test_image.exists():
            start_time = time.time()
            try:
                text_results = main_ocr_engine.recognize_text(str(test_image))
                processing_time = time.time() - start_time
                
                print(f"✅ 主程序识别成功 ({processing_time:.2f}秒)")
                print(f"识别结果: {len(text_results)} 个TextResult对象")
                
                for i, text_result in enumerate(text_results[:3]):
                    print(f"   {i+1}. '{text_result.text}' (置信度: {text_result.confidence:.2f})")
                
                return True
                
            except Exception as e:
                processing_time = time.time() - start_time
                print(f"❌ 主程序识别失败: {e} ({processing_time:.2f}秒)")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("⚠️ 测试图片不存在，跳过识别测试")
            return True
        
    except Exception as e:
        print(f"❌ 主程序集成诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_file_permissions():
    """检查文件权限"""
    print("\n" + "=" * 50)
    print("🔍 文件权限检查")
    print("=" * 50)
    
    # 检查测试图片目录
    test_image_dir = project_root / "test_image"
    if test_image_dir.exists():
        print(f"✅ 测试图片目录存在: {test_image_dir}")
        
        image_files = list(test_image_dir.glob("*.jpg"))
        print(f"找到 {len(image_files)} 张图片")
        
        # 检查前几张图片的权限
        for i, image_file in enumerate(image_files[:3]):
            try:
                # 尝试读取文件
                with open(image_file, 'rb') as f:
                    f.read(1024)  # 读取前1KB
                print(f"✅ {image_file.name} - 可读")
            except Exception as e:
                print(f"❌ {image_file.name} - 读取失败: {e}")
    else:
        print(f"❌ 测试图片目录不存在: {test_image_dir}")
    
    # 检查缓存目录
    cache_dir = project_root / "cache"
    if cache_dir.exists():
        print(f"✅ 缓存目录存在: {cache_dir}")
    else:
        print(f"❌ 缓存目录不存在: {cache_dir}")
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建缓存目录成功")
        except Exception as e:
            print(f"❌ 创建缓存目录失败: {e}")

def main():
    """主诊断函数"""
    print("🔬 OCR问题全面诊断")
    
    # 检查文件权限
    check_file_permissions()
    
    # 诊断缓存问题
    cache_ok = diagnose_cache_issues()
    
    # 诊断OCR引擎问题
    ocr_ok = diagnose_ocr_engine()
    
    # 诊断主程序集成问题
    integration_ok = diagnose_main_program_integration()
    
    print("\n" + "=" * 50)
    print("📋 诊断结果总结")
    print("=" * 50)
    
    print(f"缓存系统: {'✅ 正常' if cache_ok else '❌ 异常'}")
    print(f"OCR引擎: {'✅ 正常' if ocr_ok else '❌ 异常'}")
    print(f"主程序集成: {'✅ 正常' if integration_ok else '❌ 异常'}")
    
    if cache_ok and ocr_ok and integration_ok:
        print("\n🎉 所有系统正常，问题可能在其他地方")
    else:
        print("\n⚠️ 发现问题，需要进一步修复")
        
        if not cache_ok:
            print("- 缓存系统有问题")
        if not ocr_ok:
            print("- OCR引擎有问题")
        if not integration_ok:
            print("- 主程序集成有问题")

if __name__ == "__main__":
    main()
