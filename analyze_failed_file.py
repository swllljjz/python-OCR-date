#!/usr/bin/env python3
"""
分析OCR失败文件的特征
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def analyze_failed_files():
    """分析OCR失败的文件"""
    print("🔍 OCR失败文件分析")
    print("=" * 60)
    
    try:
        from core.image_analyzer import ImageAnalyzer
        
        # 创建图片分析器
        analyzer = ImageAnalyzer()
        
        # 测试图片目录
        test_image_dir = project_root / "test_image"
        
        # 已知的失败文件
        failed_files = ["2025.06.24.jpg"]
        
        print(f"分析 {len(failed_files)} 个失败文件...")
        
        for failed_file in failed_files:
            file_path = test_image_dir / failed_file
            
            if not file_path.exists():
                print(f"❌ 文件不存在: {failed_file}")
                continue
            
            # 分析失败文件
            analysis = analyzer.analyze_failed_file(str(file_path))
            
            if 'error' not in analysis:
                # 获取推荐策略
                strategy = analyzer.get_optimization_strategy(analysis)
                print(f"\n🎯 推荐策略: {strategy}")
                
                # 保存分析结果
                analyzer.analysis_results[failed_file] = analysis
        
        # 对比分析成功文件
        print("\n" + "=" * 60)
        print("📊 对比分析：成功 vs 失败文件")
        print("=" * 60)
        
        # 分析几个成功的文件作为对比
        success_files = ["2012.11.26.jpg", "2021.10.29.jpg", "2025.06.25.jpg"]
        
        print("\n✅ 成功文件分析:")
        for success_file in success_files:
            file_path = test_image_dir / success_file
            if file_path.exists():
                print(f"\n--- {success_file} ---")
                analysis = analyzer.analyze_image(str(file_path))
                if 'error' not in analysis:
                    quality = analysis['quality_metrics']
                    content = analysis['content_analysis']
                    print(f"亮度: {quality['mean_brightness']:.1f}, 对比度: {quality['contrast']:.1f}, 清晰度: {quality['sharpness']:.1f}")
                    print(f"文本区域: {content['text_like_regions']}, OCR难度: {analysis['ocr_difficulty']}")
        
        # 总结分析
        print("\n" + "=" * 60)
        print("📋 分析总结")
        print("=" * 60)
        
        if failed_files[0] in analyzer.analysis_results:
            failed_analysis = analyzer.analysis_results[failed_files[0]]
            
            print("失败文件特征:")
            quality = failed_analysis['quality_metrics']
            content = failed_analysis['content_analysis']
            
            print(f"- 亮度: {quality['mean_brightness']:.1f}")
            print(f"- 对比度: {quality['contrast']:.1f}")
            print(f"- 清晰度: {quality['sharpness']:.1f}")
            print(f"- 文本区域: {content['text_like_regions']}")
            print(f"- OCR难度: {failed_analysis['ocr_difficulty']}")
            
            print(f"\n建议的解决方案:")
            for suggestion in failed_analysis['preprocessing_suggestions']:
                print(f"- {suggestion}")
        
        return analyzer.analysis_results
        
    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = analyze_failed_files()
    
    if results:
        print("\n🎉 分析完成！")
        print("基于分析结果，将实施针对性的优化策略。")
    else:
        print("❌ 分析失败，请检查错误信息")
