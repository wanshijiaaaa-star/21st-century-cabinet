#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML to Markdown Converter Tool

This module provides a tool for converting HTML content to Markdown format.
It uses the markdownify library for conversion with additional preprocessing
and postprocessing to handle special cases.

Usage Examples:
    # 从HTML字符串转换
    from tools.mdtools.html2doc import html_to_markdown
    markdown_content = html_to_markdown(html_content)
    
    # 保存到文件
    html_to_markdown_file(html_content, 'output.md')

Author: AI Assistant
Date: 2025/04/15
"""

import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

try:
    from markdownify import markdownify as md
except ImportError:
    raise ImportError("请安装 markdownify 库: pip install markdownify")


def html_to_markdown(html_content: str, 
                    config: Optional[Dict[str, Any]] = None) -> str:
    """
    将 HTML 内容转换为 Markdown
    
    Args:
        html_content: HTML 内容
        config: 配置选项，支持：
            - heading_style: 标题样式 ("ATX" 或 "underlined")
            - bullets: 列表符号 (默认 "-*+")
            - strip: 要移除的标签列表
            - escape_asterisks: 是否转义星号
            - escape_underscores: 是否转义下划线
            
    Returns:
        Markdown 内容
    """
    if not html_content:
        return ""
    
    # 默认配置
    default_config = {
        'heading_style': 'ATX',
        'bullets': '-*+',
        'strip': [],
        'escape_asterisks': False,
        'escape_underscores': False,
        'remove_images': False,
        'remove_links': False,
    }
    
    if config:
        default_config.update(config)
    
    try:
        # 预处理 HTML
        processed_html = _preprocess_html(html_content, default_config)
        
        # 转换为 Markdown
        markdown_content = md(
            processed_html,
            heading_style=default_config['heading_style'],
            bullets=default_config['bullets'],
            strip=default_config['strip'],
            escape_asterisks=default_config['escape_asterisks'],
            escape_underscores=default_config['escape_underscores']
        )
        
        # 后处理 Markdown
        markdown_content = _postprocess_markdown(markdown_content)
        
        return markdown_content
        
    except Exception as e:
        print(f"HTML 转 Markdown 失败: {e}")
        return ""


def _preprocess_html(html_content: str, config: Dict[str, Any]) -> str:
    """
    预处理 HTML 内容
    
    Args:
        html_content: 原始 HTML 内容
        config: 配置选项
        
    Returns:
        处理后的 HTML 内容
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除不需要的标签
        for tag in soup.find_all(['span', 'font', 'div']):
            tag.unwrap()
        
        # 移除样式和类属性
        for tag in soup.find_all(True):
            if 'style' in tag.attrs:
                del tag.attrs['style']
            if 'class' in tag.attrs:
                del tag.attrs['class']
            if 'data-pm-slice' in tag.attrs:
                del tag.attrs['data-pm-slice']
            if 'data-title' in tag.attrs:
                del tag.attrs['data-title']
        
        # 处理图片
        if config.get('remove_images', False):
            for img in soup.find_all('img'):
                img.decompose()
        else:
            # 保留图片的 title 属性作为 alt
            for img in soup.find_all('img'):
                if 'title' in img.attrs and 'alt' not in img.attrs:
                    img['alt'] = img['title']
        
        # 处理链接
        if config.get('remove_links', False):
            for a in soup.find_all('a'):
                a.unwrap()
        
        content = str(soup)
        
        # 替换 p 标签中的换行符
        content = re.sub(
            r'(<p[^>]*>)([\s\S]*?)(</p>)',
            lambda m: m.group(1) + re.sub(r'\n', '', m.group(2)) + m.group(3),
            content
        )
        
        # 清理多余换行
        content = re.sub(r'\n\s*\n\s*\n+', '\n', content)
        
        return content
        
    except Exception as e:
        print(f"HTML 预处理失败: {e}")
        return html_content


def _postprocess_markdown(markdown_content: str) -> str:
    """
    后处理 Markdown 内容
    
    Args:
        markdown_content: 原始 Markdown 内容
        
    Returns:
        处理后的 Markdown 内容
    """
    try:
        # 清理多余换行
        markdown_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', markdown_content)
        
        # 移除多余的星号（可能是转换错误）
        markdown_content = re.sub(r'\*{3,}', '**', markdown_content)
        
        # 确保标题前后有空行
        markdown_content = re.sub(r'([^\n])\n(#{1,6} )', r'\1\n\n\2', markdown_content)
        markdown_content = re.sub(r'(#{1,6} [^\n]+)\n([^\n#])', r'\1\n\n\2', markdown_content)
        
        return markdown_content.strip()
        
    except Exception as e:
        print(f"Markdown 后处理失败: {e}")
        return markdown_content


def html_to_markdown_file(html_content: str, 
                         output_file: str,
                         document_title: Optional[str] = None,
                         config: Optional[Dict[str, Any]] = None) -> bool:
    """
    将 HTML 转换为 Markdown 并保存到文件
    
    Args:
        html_content: HTML 内容
        output_file: 输出的 Markdown 文件路径
        document_title: 文档标题（将添加到文件开头）
        config: 配置选项
        
    Returns:
        是否成功
    """
    try:
        # 转换为 Markdown
        markdown_content = html_to_markdown(html_content, config)
        
        # 添加标题
        if document_title:
            markdown_content = f"# {document_title}\n\n{markdown_content}"
        
        # 保存文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Markdown 文件已保存: {output_file}")
        return True
        
    except Exception as e:
        print(f"保存 Markdown 文件失败: {e}")
        return False


# 配置预设
DEFAULT_CONFIG = {
    'heading_style': 'ATX',
    'bullets': '-*+',
    'escape_asterisks': False,
    'escape_underscores': False,
}

# 简洁配置（移除图片和链接）
CLEAN_CONFIG = {
    'heading_style': 'ATX',
    'bullets': '-*+',
    'remove_images': True,
    'remove_links': True,
}


if __name__ == '__main__':
    # 测试示例
    test_html = """
    <h1>标题测试</h1>
    <p>这是一个 <strong>粗体</strong> 和 <em>斜体</em> 的示例。</p>
    <h2>列表示例</h2>
    <ul>
        <li>项目 1</li>
        <li>项目 2</li>
    </ul>
    <h2>代码示例</h2>
    <pre><code>def hello_world():
    print("Hello, World!")</code></pre>
    <h2>表格示例</h2>
    <table>
        <tr><th>列1</th><th>列2</th></tr>
        <tr><td>A</td><td>B</td></tr>
    </table>
    """
    
    markdown = html_to_markdown(test_html)
    print("转换结果：")
    print(markdown)
