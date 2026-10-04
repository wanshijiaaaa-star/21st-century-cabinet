# 微信公众号文章类型检测器

## 文章类型定义

- **0 = 图文**：普通文章，包含文字和图片
- **5 = 视频**：包含视频内容
- **7 = 音频**：包含音频内容
- **10 = 贴图**：主要是图片，文字很少
- **11 = 分享**：分享链接类型

## 文件说明

1. **article_type_detector.py** - 基础版本检测器
2. **article_type_detector_enhanced.py** - 增强版本检测器（推荐使用）

## 使用方法

### 方法1：直接检测URL

```python
from article_type_detector_enhanced import ArticleTypeDetector

detector = ArticleTypeDetector()
result = detector.detect_type('https://mp.weixin.qq.com/s/xxxxx')

print(f"文章类型: {result['type']} - {result['type_name']}")
```

### 方法2：批量检测

```python
from article_type_detector_enhanced import ArticleTypeDetector, print_result

urls = [
    'https://mp.weixin.qq.com/s/xxxxx1',
    'https://mp.weixin.qq.com/s/xxxxx2',
    'https://mp.weixin.qq.com/s/xxxxx3'
]

detector = ArticleTypeDetector()
results = detector.batch_detect(urls)

for i, result in enumerate(results, 1):
    print_result(result, i)
```

### 方法3：从HTML内容检测

```python
from article_type_detector_enhanced import ArticleTypeDetector

# 假设你已经获取了完整的HTML内容
html_content = """
<!DOCTYPE html>
<html>
...
</html>
"""

detector = ArticleTypeDetector()
result = detector.detect_type_from_html(html_content)

print(f"文章类型: {result['type']} - {result['type_name']}")
```

## 检测原理

检测器通过分析HTML内容中的特征来判断文章类型：

### 视频检测
- 查找 `<iframe class="video_iframe">` 标签
- 查找 `<video>` 标签
- 查找 `<mpvideo>` 标签
- 查找 `data-type="video"` 属性
- 查找视频相关的JavaScript变量

### 音频检测
- 查找 `<mpvoice>` 标签
- 查找 `<audio>` 标签
- 查找 `data-type="audio"` 属性
- 查找音频相关的JavaScript变量

### 图片检测
- 查找 `<img class="rich_pages">` 标签
- 查找 `data-type="jpeg|png|gif|webp"` 属性
- 查找微信图片域名（mmbiz.qpic.cn, mmbiz.qlogo.cn）

### 分享检测
- 查找 `data-type="share"` 属性
- 查找分享卡片相关元素

### 贴图判断
- 图片数量 >= 3
- 文本长度 < 200 或段落数 < 3

## 注意事项

1. **JavaScript渲染问题**：微信公众号文章可能需要JavaScript渲染才能获取完整内容。如果直接请求URL无法获取完整内容，建议：
   - 使用Selenium或Playwright等工具获取完整HTML
   - 从微信后台API获取文章信息
   - 使用浏览器开发者工具手动获取HTML

2. **反爬虫机制**：微信可能有反爬虫机制，建议：
   - 设置合理的请求间隔
   - 使用真实的User-Agent
   - 添加Cookie等认证信息

3. **准确性**：检测结果基于HTML特征分析，可能存在误判，建议结合实际情况验证。

## 示例输出

```
文章1: 这是一个视频文章标题...
  类型: 5 - 视频
  特征:
    - 视频: True (数量: 1)
    - 音频: False (数量: 0)
    - 图片: False (数量: 0)
    - 分享: False
    - 文本长度: 150 字符
    - 段落数: 2
```

## 依赖安装

```bash
pip install requests beautifulsoup4
```

## 扩展建议

如果需要更准确的检测，可以考虑：

1. **使用Selenium**：获取JavaScript渲染后的完整HTML
2. **接入微信API**：通过官方API获取文章信息
3. **机器学习**：训练模型识别文章类型
4. **人工标注**：建立标注数据集，提高准确率
