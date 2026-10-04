"""
Markdown 转 HTML 工具
支持将 Markdown 内容转换为 HTML，并提供了丰富的自定义选项
"""

import markdown
from markdown.extensions import codehilite, tables, toc, fenced_code
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional, Any

from pyee.cls import on
from core.print import print_info, print_error, print_warning


class MarkdownToHtmlConverter:
    """Markdown 转 HTML 转换器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化转换器
        
        Args:
            config: 配置字典，支持以下选项：
                - extensions: 启用的扩展列表
                - remove_images: 是否移除图片
                - remove_links: 是否移除链接
                - add_css_class: 添加CSS类名
                - custom_css: 自定义CSS样式
                - pretty_print: 是否格式化输出
                - allow_html: 是否允许HTML标签
        """
        self.config = config or {}
        self.default_extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.footnotes',
            'markdown.extensions.attr_list',
            'markdown.extensions.def_list',
            'markdown.extensions.abbr',
            'markdown.extensions.md_in_html'
        ]
        
        # 设置默认配置
        self.only_body = self.config.get('only_body', True)
        self.extensions = self.config.get('extensions', self.default_extensions)
        self.remove_images = self.config.get('remove_images', False)
        self.remove_links = self.config.get('remove_links', False)
        self.add_css_class = self.config.get('add_css_class', True)
        self.custom_css = self.config.get('custom_css', '')
        self.pretty_print = self.config.get('pretty_print', True)
        self.allow_html = self.config.get('allow_html', True)
        
        # 配置扩展
        self.extension_configs = {
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True
            },
            'toc': {
                'permalink': True,
                'permalink_class': 'headerlink'
            },
            'tables': {},
            'fenced_code': {}
        }
        
        # 更新扩展配置
        if 'extension_configs' in self.config:
            self.extension_configs.update(self.config['extension_configs'])
    
    def convert(self, markdown_content: str) -> str:
        """
        将 Markdown 内容转换为 HTML
        
        Args:
            markdown_content: Markdown 内容
            
        Returns:
            HTML 内容
        """
        try:
            # 创建 Markdown 实例
            md = markdown.Markdown(
                extensions=self.extensions,
                extension_configs=self.extension_configs
            )
            
            # 转换为 HTML
            html_content = md.convert(markdown_content)
            
            # 后处理
            html_content = self._post_process_html(html_content)
            
            # 添加包装结构
            html_content = self._wrap_html(html_content)
            
            return html_content
            
        except Exception as e:
            print_error(f"Markdown 转 HTML 失败: {e}")
            return f"<p>转换失败: {str(e)}</p>"
    
    def convert_with_metadata(self, markdown_content: str) -> Dict[str, Any]:
        """
        转换 Markdown 并返回元数据
        
        Args:
            markdown_content: Markdown 内容
            
        Returns:
            包含 HTML 和元数据的字典
        """
        try:
            md = markdown.Markdown(
                extensions=self.extensions,
                extension_configs=self.extension_configs
            )
            
            html_content = md.convert(markdown_content)
            html_content = self._post_process_html(html_content)
            html_content = self._wrap_html(html_content,only_body=self.only_body)
            
            # 提取元数据
            metadata = {
                'toc': getattr(md, 'toc', ''),
                'toc_tokens': getattr(md, 'toc_tokens', []),
                'meta': getattr(md, 'Meta', {}),
                'word_count': len(markdown_content.split()),
                'char_count': len(markdown_content)
            }
            
            return {
                'html': html_content,
                'metadata': metadata
            }
            
        except Exception as e:
            print_error(f"Markdown 转 HTML 失败: {e}")
            return {
                'html': f"<p>转换失败: {str(e)}</p>",
                'metadata': {}
            }
    
    def _post_process_html(self, html_content: str) -> str:
        """
        后处理 HTML 内容
        
        Args:
            html_content: 原始 HTML 内容
            
        Returns:
            处理后的 HTML 内容
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除图片
            if self.remove_images:
                for img in soup.find_all('img'):
                    img.decompose()
            
            # 移除链接
            if self.remove_links:
                for a in soup.find_all('a'):
                    # 保留链接文本，移除链接属性
                    a.unwrap()
            
            # 添加 CSS 类
            if self.add_css_class:
                self._add_css_classes(soup)
            
            # 处理代码块
            self._process_code_blocks(soup)
            
            # 处理表格
            self._process_tables(soup)
            
            # 处理图片
            self._process_images(soup)
            
            return str(soup)
            
        except Exception as e:
            print_error(f"HTML 后处理失败: {e}")
            return html_content
    
    def _add_css_classes(self, soup: BeautifulSoup):
        """添加 CSS 类名"""
        # 为代码块添加类
        for pre in soup.find_all('pre'):
            if not pre.get('class'):
                pre['class'] = pre.get('class', []) + ['code-block']
        
        # 为表格添加类
        for table in soup.find_all('table'):
            if not table.get('class'):
                table['class'] = table.get('class', []) + ['table', 'table-striped']
        
        # 为引用添加类
        for blockquote in soup.find_all('blockquote'):
            if not blockquote.get('class'):
                blockquote['class'] = blockquote.get('class', []) + ['blockquote']
        
        # 为列表添加类
        for ul in soup.find_all('ul'):
            if not ul.get('class'):
                ul['class'] = ul.get('class', []) + ['list-unstyled']
        
        for ol in soup.find_all('ol'):
            if not ol.get('class'):
                ol['class'] = ol.get('class', []) + ['list-numbered']
    
    def _process_code_blocks(self, soup: BeautifulSoup):
        """处理代码块"""
        for code in soup.find_all('code'):
            # 为内联代码添加类
            if not code.get('class'):
                code['class'] = code.get('class', []) + ['inline-code']
    
    def _process_tables(self, soup: BeautifulSoup):
        """处理表格"""
        for table in soup.find_all('table'):
            # 添加响应式包装
            if not table.find_parent('div', class_='table-responsive'):
                wrapper = soup.new_tag('div', **{'class': 'table-responsive'})
                table.wrap(wrapper)
            
            # 添加表头样式
            thead = table.find('thead')
            if thead:
                thead['class'] = thead.get('class', []) + ['table-header']
    
    def _process_images(self, soup: BeautifulSoup):
        """处理图片"""
        for img in soup.find_all('img'):
            # 添加响应式类
            if not img.get('class'):
                img['class'] = img.get('class', []) + ['img-responsive', 'img-fluid']
            
            # 添加 alt 属性
            if not img.get('alt'):
                img['alt'] = '图片'
            
            # 添加 loading="lazy"
            if not img.get('loading'):
                img['loading'] = 'lazy'
    
    def _wrap_html(self, html_content: str,only_body:bool=True) -> str:
        """
        包装 HTML 内容，添加完整的 HTML 结构
        
        Args:
            html_content: 处理后的 HTML 内容
            
        Returns:
            完整的 HTML 文档
        """
        if only_body:
            return html_content
        css_styles = self._get_default_css()
        if self.custom_css:
            css_styles += '\n' + self.custom_css
        
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
{css_styles}
    </style>
</head>
<body>
    <div class="markdown-body">
{html_content}
    </div>
</body>
</html>"""
        
        return html_template
    
    def _get_default_css(self) -> str:
        """获取默认 CSS 样式"""
        return """
        /* Markdown 默认样式 */
        .markdown-body {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        
        /* 标题样式 */
        .markdown-body h1, .markdown-body h2, .markdown-body h3, 
        .markdown-body h4, .markdown-body h5, .markdown-body h6 {
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }
        
        .markdown-body h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
        .markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
        .markdown-body h3 { font-size: 1.25em; }
        .markdown-body h4 { font-size: 1em; }
        .markdown-body h5 { font-size: 0.875em; }
        .markdown-body h6 { font-size: 0.85em; color: #6a737d; }
        
        /* 段落样式 */
        .markdown-body p {
            margin-bottom: 16px;
        }
        
        /* 链接样式 */
        .markdown-body a {
            color: #0366d6;
            text-decoration: none;
        }
        
        .markdown-body a:hover {
            text-decoration: underline;
        }
        
        /* 列表样式 */
        .markdown-body ul, .markdown-body ol {
            padding-left: 2em;
            margin-bottom: 16px;
        }
        
        .markdown-body li {
            margin-bottom: 0.25em;
        }
        
        /* 引用样式 */
        .markdown-body blockquote {
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
            margin-bottom: 16px;
        }
        
        /* 代码样式 */
        .markdown-body code {
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            background-color: rgba(27, 31, 35, 0.05);
            border-radius: 3px;
        }
        
        .markdown-body pre {
            padding: 16px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            background-color: #f6f8fa;
            border-radius: 6px;
            margin-bottom: 16px;
        }
        
        .markdown-body pre code {
            display: inline;
            max-width: auto;
            padding: 0;
            margin: 0;
            overflow: visible;
            line-height: inherit;
            word-wrap: normal;
            background-color: transparent;
            border: 0;
        }
        
        /* 表格样式 */
        .markdown-body table {
            border-spacing: 0;
            border-collapse: collapse;
            margin-bottom: 16px;
            width: 100%;
        }
        
        .markdown-body table th, .markdown-body table td {
            padding: 6px 13px;
            border: 1px solid #dfe2e5;
        }
        
        .markdown-body table th {
            background-color: #f6f8fa;
            font-weight: 600;
        }
        
        .markdown-body table tr:nth-child(even) {
            background-color: #f6f8fa;
        }
        
        /* 图片样式 */
        .markdown-body img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 16px auto;
            border-radius: 6px;
        }
        
        /* 水平分割线 */
        .markdown-body hr {
            height: 0.25em;
            padding: 0;
            margin: 24px 0;
            background-color: #e1e4e8;
            border: 0;
        }
        
        /* 目录样式 */
        .markdown-body .toc {
            background-color: #f6f8fa;
            border: 1px solid #dfe2e5;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
        }
        
        .markdown-body .toc ul {
            padding-left: 1.5em;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .markdown-body {
                padding: 10px;
            }
            
            .markdown-body h1 { font-size: 1.8em; }
            .markdown-body h2 { font-size: 1.4em; }
            .markdown-body h3 { font-size: 1.2em; }
        }
        """


def convert_markdown_to_html(markdown_content: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    便捷函数：将 Markdown 转换为 HTML
    
    Args:
        markdown_content: Markdown 内容
        config: 配置选项
        
    Returns:
        HTML 内容
    """
    converter = MarkdownToHtmlConverter(config)
    return converter.convert(markdown_content)


def convert_markdown_file_to_html(input_file: str, output_file: str, 
                                 config: Optional[Dict[str, Any]] = None) -> bool:
    """
    便捷函数：将 Markdown 文件转换为 HTML 文件
    
    Args:
        input_file: 输入的 Markdown 文件路径
        output_file: 输出的 HTML 文件路径
        config: 配置选项
        
    Returns:
        是否成功
    """
    try:
        # 读取 Markdown 文件
        with open(input_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # 转换为 HTML
        html_content = convert_markdown_to_html(markdown_content, config)
        
        # 保存 HTML 文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print_info(f"成功转换 {input_file} -> {output_file}")
        return True
        
    except Exception as e:
        print_error(f"文件转换失败: {e}")
        return False


# 示例配置
DEFAULT_CONFIG = {
    'remove_images': False,
    'remove_links': False,
    'add_css_class': True,
    'pretty_print': True,
    'allow_html': True
}

# 简单配置（最小样式）
SIMPLE_CONFIG = {
    'extensions': ['markdown.extensions.extra'],
    'add_css_class': False,
    'custom_css': ''
}

# 无样式配置（仅转换，无样式）
PLAIN_CONFIG = {
    'extensions': ['markdown.extensions.extra'],
    'add_css_class': False,
    'custom_css': '',
    'pretty_print': False
}


if __name__ == "__main__":
    # 测试示例
    test_markdown = """# 标题测试

这是一个 **粗体** 和 *斜体* 的示例。

## 列表示例

- 项目 1
- 项目 2
  - 子项目 2.1
  - 子项目 2.2

## 代码示例

```python
def hello_world():
    print("Hello, World!")
```

## 表格示例

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A   | B   | C   |
| 1   | 2   | 3   |

> 这是一个引用块

[链接示例](https://example.com)
"""
    
    # 使用默认配置转换
    converter = MarkdownToHtmlConverter()
    html_result = converter.convert(test_markdown)
    print("转换结果：")
    print(html_result)