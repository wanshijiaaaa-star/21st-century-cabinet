# PDF压缩工具使用说明

## 功能特性

- 支持单个PDF文件压缩
- 支持批量压缩目录中的PDF文件
- 提供多种压缩方法
- 可调节图片压缩质量
- 显示压缩前后文件大小和压缩率

## 安装依赖

```bash
pip install PyPDF2 Pillow
```

## 使用方法

### 1. 压缩单个PDF文件

```bash
# 基础压缩(默认)
python tools/pdf_compressor.py input.pdf

# 指定输出文件名
python tools/pdf_compressor.py input.pdf -o output.pdf

# 设置图片压缩质量(1-100,默认85)
python tools/pdf_compressor.py input.pdf -q 70

# 使用图片压缩方法
python tools/pdf_compressor.py input.pdf -m images

# 显示详细信息
python tools/pdf_compressor.py input.pdf -v
```

### 2. 批量压缩PDF文件

```bash
# 压缩目录中的所有PDF文件
python tools/pdf_compressor.py -d /path/to/pdfs

# 指定输出目录
python tools/pdf_compressor.py -d /path/to/pdfs -o /path/to/output

# 批量压缩并设置质量
python tools/pdf_compressor.py -d /path/to/pdfs -q 75 -v
```

## 压缩方法说明

### basic - 基础压缩
- 重新写入PDF结构
- 移除冗余数据
- 优化PDF内部结构
- 适用于大多数PDF文件
- 压缩率适中,速度快
- **注意**: 对已优化的PDF效果不明显

### images - 图片压缩
- 压缩PDF中的图片
- 可调节图片质量
- 适用于包含大量图片的PDF
- 压缩率较高,可能影响图片质量

### aggressive - 激进压缩 (推荐)
- 深度压缩所有图片资源
- 重新编码JPEG图片(可调质量)
- 优化PNG/无损压缩数据
- 适用于包含大量图片的PDF
- **压缩效果最好**,推荐使用
- 可能轻微影响图片质量,但肉眼几乎看不出差异

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| input | 输入PDF文件路径 | - |
| -o, --output | 输出PDF文件路径 | input_compressed.pdf |
| -d, --dir | 批量处理目录 | - |
| -q, --quality | 图片压缩质量(1-100) | 85 |
| -m, --method | 压缩方法(basic/images/aggressive) | aggressive |
| -v, --verbose | 显示详细信息 | False |

## 使用示例

### 示例1: 压缩报告文件

```bash
python tools/pdf_compressor.py report.pdf -m aggressive -q 60 -v
```

输出:
```
原始文件大小: 21.43 MB
压缩方法: aggressive
图片质量: 60
处理第 1 页...
  图片 /IM8: 2191x3155
    压缩: 391593 -> 297419 bytes (24.0%)
...
压缩后文件大小: 16.04 MB
压缩率: 25.17%

✓ 激进压缩完成 (处理了 43 张图片,压缩了 43 张)
原始大小: 21.43 MB
压缩后大小: 16.04 MB
压缩率: 25.17%
输出文件: report_compressed.pdf
```

### 示例2: 批量压缩

```bash
python tools/pdf_compressor.py -d ./pdfs -q 75 -v
```

输出:
```
找到 10 个PDF文件

[1/10] 处理: doc1.pdf
✓ 基础压缩完成
  2.34 MB -> 1.56 MB (33.33%)

[2/10] 处理: doc2.pdf
✓ 基础压缩完成
  4.12 MB -> 2.89 MB (29.85%)

...

完成! 成功压缩 10/10 个文件
```

## 注意事项

1. **备份重要文件**: 压缩前建议备份原始PDF文件
2. **图片质量**: 降低图片质量会减小文件大小,但可能影响清晰度
3. **压缩率**: 不同PDF的压缩率差异较大,取决于PDF内容
4. **批量处理**: 批量处理会在输入目录下创建compressed子目录

## 常见问题

### Q: 为什么压缩后文件反而变大了?
A: 某些PDF已经经过优化,再次压缩可能无效。建议尝试不同的压缩方法。

### Q: 压缩后PDF无法打开怎么办?
A: 可能是压缩过程中出现问题,请使用原始文件,并尝试使用basic方法。

### Q: 如何获得最佳压缩效果?
A: 建议先尝试basic方法,如果效果不明显,再使用images方法并调整质量参数。

## 技术实现

- 使用PyPDF2库处理PDF文件结构
- 使用Pillow库处理图片压缩
- 支持JPEG和PNG图片格式
- 保持PDF原有功能和布局
