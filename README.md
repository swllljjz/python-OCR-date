# 🔍 商品包装生产日期识别系统

基于PaddleOCR深度学习技术的智能日期识别系统，专门用于识别商品包装上的生产日期信息。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.7+-green.svg)](https://github.com/PaddlePaddle/PaddleOCR)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 功能特性

- 🎯 **高精度识别**: 基于PaddleOCR的专业中文OCR识别，识别率达78.6%+
- 📅 **多格式支持**: 支持YYYY-MM-DD、YYYY/MM/DD、YYYY.MM.DD等多种日期格式
- 🖼️ **智能预处理**: 自动图像增强、尺寸调整、去噪处理
- ⚡ **批量处理**: 支持多文件并行处理，提升工作效率
- 🖥️ **友好界面**: 基于Tkinter的直观GUI界面
- 📊 **详细报告**: 提供识别结果统计和性能分析

## 🚀 性能表现

| 指标 | 当前表现 |
|------|----------|
| **OCR识别率** | 78.6% |
| **日期识别率** | 78.6% |
| **平均处理时间** | 14.36秒/张 |
| **支持格式** | 10+ 种日期格式 |

## 🛠️ 技术栈

- **OCR引擎**: PaddleOCR (专业中文识别)
- **图像处理**: OpenCV + 自适应增强算法
- **深度学习**: PaddlePaddle框架
- **界面框架**: Python Tkinter
- **架构设计**: 模块化 + 插件式

## 📦 快速开始

### 环境要求

- Python 3.8+
- Windows/Linux/macOS
- 内存: 4GB+ (推荐8GB+)
- 存储: 2GB+ (用于OCR模型)

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/swllljjz/python-OCR-date.git
cd python-OCR-date
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行程序**
```bash
python v1/main.py
```

### 首次运行

首次运行时，PaddleOCR会自动下载模型文件（约500MB），请确保网络连接正常。

## 📁 项目结构

```
python-OCR-date/
├── 📂 core/                    # 核心功能模块
│   ├── 🔧 ocr_engine.py       # OCR引擎管理
│   ├── 🔧 paddleocr_engine.py # PaddleOCR引擎
│   ├── 🔧 date_recognizer.py  # 日期识别器
│   ├── 🔧 image_processor.py  # 图像处理器
│   └── 📊 models.py           # 数据模型
├── 📂 v1/                     # 主程序 (GUI版本)
│   ├── 🖥️ main.py            # 程序入口
│   ├── 📂 gui/               # 界面组件
│   └── 📂 handlers/          # 业务处理器
├── 📂 config/                 # 配置文件
│   ├── ⚙️ settings.yaml      # 主配置文件
│   └── 📝 logging.yaml       # 日志配置
├── 📂 docs/                   # 项目文档
├── 📂 test_image/             # 测试图片样本
├── 📋 requirements.txt        # 依赖列表
└── 📖 README.md              # 项目说明
```

## 🎯 使用方法

### GUI界面使用

1. **启动程序**: 运行 `python v1/main.py`
2. **选择文件**: 点击"选择文件夹"或"选择文件"
3. **开始识别**: 点击"开始处理"按钮
4. **查看结果**: 在结果面板查看识别到的日期信息
5. **导出结果**: 可导出为Excel或CSV格式

### 命令行使用

```python
from core.date_recognizer import create_date_recognizer

# 创建日期识别器
recognizer = create_date_recognizer()

# 识别单张图片
result = recognizer.recognize_single("path/to/image.jpg")

if result.success:
    print(f"识别到的日期: {result.dates_found}")
    print(f"置信度: {result.confidence}")
```

## 📊 识别示例

| 输入图片 | 识别结果 | 置信度 |
|----------|----------|--------|
| 包装上的"2025-06-25" | 2025-06-25 | 99% |
| "生产日期：2021/10/29" | 2021-10-29 | 98% |
| "2024/12/26" | 2024-12-26 | 98% |

## ⚙️ 配置说明

主要配置文件：`config/settings.yaml`

```yaml
# OCR引擎配置
ocr:
  engine: "paddleocr"           # OCR引擎类型
  language: "ch"                # 识别语言
  confidence_threshold: 0.8     # 置信度阈值

# 性能配置
performance:
  single_image_timeout: 45      # 单图超时时间
  batch_timeout: 1200          # 批量处理超时
```

## 🔧 开发指南

### 添加新的OCR引擎

1. 在`core/`目录下创建新的引擎文件
2. 继承`BaseOCREngine`类
3. 实现`ocr()`方法
4. 在`ocr_engine.py`中注册新引擎

### 添加新的日期格式

1. 修改`core/date_parser.py`
2. 添加新的正则表达式模式
3. 更新测试用例

## 🐛 故障排除

### 常见问题

1. **PaddleOCR初始化失败**
   - 检查网络连接
   - 确保有足够的存储空间
   - 尝试重新安装：`pip install --upgrade paddlepaddle paddleocr`

2. **识别率低**
   - 检查图片质量和清晰度
   - 尝试调整置信度阈值
   - 使用图片预处理功能

3. **处理速度慢**
   - 减少图片尺寸
   - 调整超时设置
   - 考虑使用GPU加速

## 📈 性能优化

系统提供多种优化选项：

- **图片预处理**: 自动尺寸调整和质量增强
- **动态超时**: 根据图片大小自动调整处理时间
- **多策略处理**: 失败时自动尝试不同的处理方法
- **结果缓存**: 避免重复处理相同图片

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 作者

- **开发者**: swllljjz
- **邮箱**: 165685698+swllljjz@users.noreply.github.com

## 🙏 致谢

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - 优秀的OCR框架
- [OpenCV](https://opencv.org/) - 强大的图像处理库
- [PaddlePaddle](https://www.paddlepaddle.org.cn/) - 深度学习框架

---

⭐ 如果这个项目对您有帮助，请给个Star支持一下！
