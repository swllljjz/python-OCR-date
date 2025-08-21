#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品包装生产日期识别系统启动脚本

简化的启动入口，自动处理路径和依赖问题
"""

import sys
import os
from pathlib import Path

def main():
    """主函数"""
    print("商品包装生产日期识别系统 V1.0")
    print("=" * 50)
    
    # 确保在正确的目录中
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 添加项目根目录到Python路径
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    try:
        # 导入并运行主程序
        from v1.main import main as run_main
        run_main()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保所有必需的模块都已正确安装")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
