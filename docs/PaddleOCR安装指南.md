# PaddleOCR安装指南

## 概述

本系统默认使用PaddleOCR作为OCR引擎，提供高精度的文字识别功能。如果PaddleOCR未安装，系统会自动使用模拟OCR引擎进行演示。

## 快速安装

### 方法一：标准安装（推荐）

```bash
# 安装PaddlePaddle CPU版本
pip install paddlepaddle

# 安装PaddleOCR
pip install paddleocr
```

### 方法二：GPU加速版本（可选）

如果您有NVIDIA GPU并希望获得更快的处理速度：

```bash
# 安装PaddlePaddle GPU版本
pip install paddlepaddle-gpu

# 安装PaddleOCR
pip install paddleocr
```

### 方法三：最小化安装

如果遇到依赖冲突，可以尝试最小化安装：

```bash
# 仅安装核心组件
pip install paddlepaddle paddleocr --no-deps

# 然后手动安装必需依赖
pip install numpy pillow opencv-python
```

## 验证安装

运行以下命令验证安装是否成功：

```bash
python test_paddleocr_install.py
```

或者在Python中测试：

```python
import paddleocr

# 创建OCR实例
ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang='ch')

# 测试识别
result = ocr.ocr('test_image/2025.06.24.jpg')
print("安装成功！")
```

## 常见问题

### 1. 安装速度慢

**问题**: pip安装速度很慢
**解决方案**: 使用国内镜像源

```bash
# 使用清华镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple paddlepaddle paddleocr

# 或使用阿里镜像
pip install -i https://mirrors.aliyun.com/pypi/simple/ paddlepaddle paddleocr
```

### 2. 依赖冲突

**问题**: 与现有包版本冲突
**解决方案**: 使用虚拟环境

```bash
# 创建虚拟环境
python -m venv paddle_env

# 激活虚拟环境
# Windows:
paddle_env\Scripts\activate
# macOS/Linux:
source paddle_env/bin/activate

# 在虚拟环境中安装
pip install paddlepaddle paddleocr
```

### 3. Windows安装问题

**问题**: Windows下安装失败
**解决方案**: 

1. 确保Python版本兼容（3.7-3.11）
2. 更新pip到最新版本：`python -m pip install --upgrade pip`
3. 安装Visual C++运行库
4. 使用预编译包：`pip install paddlepaddle -f https://www.paddlepaddle.org.cn/whl/windows/mkl/avx/stable.html`

### 4. macOS安装问题

**问题**: macOS下安装失败
**解决方案**:

```bash
# 对于Intel Mac
pip install paddlepaddle

# 对于Apple Silicon Mac (M1/M2)
pip install paddlepaddle
```

### 5. 内存不足

**问题**: 运行时内存不足
**解决方案**: 调整配置参数

```python
# 在配置文件中设置较小的模型
ocr = paddleocr.PaddleOCR(
    use_angle_cls=True,
    lang='ch',
    det_limit_side_len=960,  # 降低检测分辨率
    det_limit_type='min'     # 使用最小限制
)
```

## 性能优化

### 1. GPU加速

如果有NVIDIA GPU：

```bash
# 安装CUDA版本
pip install paddlepaddle-gpu
```

在代码中启用GPU：

```python
ocr = paddleocr.PaddleOCR(
    use_angle_cls=True,
    lang='ch',
    use_gpu=True
)
```

### 2. 模型缓存

首次运行时，PaddleOCR会下载模型文件（约几百MB），这些文件会缓存在本地：

- Windows: `C:\Users\{用户名}\.paddleocr\`
- macOS/Linux: `~/.paddleocr/`

### 3. 批量处理优化

对于批量处理，建议：

1. 复用OCR实例，避免重复初始化
2. 使用多线程处理多个文件
3. 适当调整图像分辨率

## 模拟OCR vs 真实OCR

### 模拟OCR引擎
- **用途**: 演示和测试
- **特点**: 返回固定的模拟结果
- **优势**: 无需安装，启动快速
- **劣势**: 无法识别真实图像内容

### 真实PaddleOCR引擎
- **用途**: 生产环境
- **特点**: 真实识别图像中的文字
- **优势**: 高精度识别，支持多种语言
- **劣势**: 需要安装，首次启动较慢

## 技术支持

如果遇到安装问题：

1. 查看系统日志：`logs/app.log`
2. 运行诊断脚本：`python test_paddleocr_install.py`
3. 参考PaddleOCR官方文档：https://github.com/PaddlePaddle/PaddleOCR
4. 联系技术支持

## 版本兼容性

| Python版本 | PaddlePaddle | PaddleOCR | 状态 |
|-----------|-------------|-----------|------|
| 3.7       | ✓           | ✓         | 支持 |
| 3.8       | ✓           | ✓         | 推荐 |
| 3.9       | ✓           | ✓         | 推荐 |
| 3.10      | ✓           | ✓         | 推荐 |
| 3.11      | ✓           | ✓         | 支持 |
| 3.12      | ✓           | ✓         | 支持 |

## 总结

PaddleOCR是一个强大的OCR引擎，虽然安装可能需要一些时间，但它提供了出色的识别精度和性能。如果您只是想快速体验系统功能，可以先使用模拟OCR引擎，之后再安装真实的PaddleOCR。
