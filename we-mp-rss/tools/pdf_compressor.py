#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF压缩工具
支持多种压缩方式：降低图片质量、移除重复资源、压缩PDF结构等
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Tuple

try:
    from PyPDF2 import PdfReader, PdfWriter
    from PIL import Image
    import io
    import zlib
except ImportError as e:
    print(f"缺少必要的依赖库: {e}")
    print("请安装依赖: pip install PyPDF2 Pillow")
    sys.exit(1)


class PDFCompressor:
    """PDF压缩器类"""

    def __init__(self, quality: int = 85, verbose: bool = False):
        """
        初始化压缩器

        Args:
            quality: 图片压缩质量 (1-100)
            verbose: 是否显示详细信息
        """
        self.quality = quality
        self.verbose = verbose

    def get_file_size(self, file_path: str) -> int:
        """获取文件大小(字节)"""
        return os.path.getsize(file_path)

    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def compress_image_in_pdf(self, image_data: bytes) -> bytes:
        """
        压缩PDF中的图片

        Args:
            image_data: 原始图片数据

        Returns:
            压缩后的图片数据
        """
        try:
            # 打开图片
            img = Image.open(io.BytesIO(image_data))

            # 转换为RGB模式(如果需要)
            if img.mode in ('RGBA', 'LA', 'P'):
                # 保持透明度
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert('RGB')

            # 压缩图片
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=self.quality, optimize=True)
            return output.getvalue()

        except Exception as e:
            if self.verbose:
                print(f"图片压缩失败: {e}")
            return image_data

    def compress_pdf_basic(self, input_path: str, output_path: str) -> Tuple[bool, str]:
        """
        基础PDF压缩方法 - 重新写入PDF以优化结构

        Args:
            input_path: 输入PDF路径
            output_path: 输出PDF路径

        Returns:
            (成功标志, 消息)
        """
        try:
            # 读取PDF
            reader = PdfReader(input_path)
            writer = PdfWriter()

            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)

            # 写入压缩后的PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            return True, "基础压缩完成"

        except Exception as e:
            return False, f"压缩失败: {e}"

    def compress_pdf_aggressive(self, input_path: str, output_path: str) -> Tuple[bool, str]:
        """
        激进压缩方法 - 压缩所有图片并优化PDF结构

        Args:
            input_path: 输入PDF路径
            output_path: 输出PDF路径

        Returns:
            (成功标志, 消息)
        """
        try:
            reader = PdfReader(input_path)
            writer = PdfWriter()

            image_count = 0
            compressed_count = 0

            for page_num, page in enumerate(reader.pages):
                if self.verbose:
                    print(f"处理第 {page_num + 1} 页...")

                # 获取页面资源
                if '/Resources' in page and '/XObject' in page['/Resources']:
                    x_object = page['/Resources']['/XObject'].get_object()

                    for obj_name in x_object:
                        obj = x_object[obj_name].get_object()

                        # 检查是否为图片
                        if obj.get('/Subtype') == '/Image':
                            image_count += 1
                            try:
                                # 获取图片尺寸
                                width = obj.get('/Width', 0)
                                height = obj.get('/Height', 0)

                                if self.verbose:
                                    print(f"  图片 {obj_name}: {width}x{height}")

                                # 尝试提取并重新压缩图片
                                if '/Filter' in obj:
                                    filter_type = obj['/Filter']

                                    # 处理DCTDecode (JPEG)
                                    if filter_type == '/DCTDecode':
                                        try:
                                            # 获取图片数据
                                            data = obj._data

                                            # 尝试用PIL重新压缩
                                            try:
                                                img = Image.open(io.BytesIO(data))
                                                output = io.BytesIO()

                                                # 根据图片模式选择保存格式
                                                if img.mode in ('RGBA', 'LA', 'P'):
                                                    if img.mode == 'RGBA':
                                                        background = Image.new('RGB', img.size, (255, 255, 255))
                                                        background.paste(img, mask=img.split()[3])
                                                        img = background
                                                    else:
                                                        img = img.convert('RGB')

                                                img.save(output, format='JPEG',
                                                        quality=self.quality,
                                                        optimize=True,
                                                        progressive=True)

                                                # 更新图片数据
                                                new_data = output.getvalue()
                                                if len(new_data) < len(data):
                                                    obj._data = new_data
                                                    compressed_count += 1
                                                    if self.verbose:
                                                        reduction = (1 - len(new_data) / len(data)) * 100
                                                        print(f"    压缩: {len(data)} -> {len(new_data)} bytes ({reduction:.1f}%)")

                                            except Exception as e:
                                                if self.verbose:
                                                    print(f"    图片处理失败: {e}")

                                        except Exception as e:
                                            if self.verbose:
                                                print(f"    JPEG处理失败: {e}")

                                    # 处理FlateDecode (PNG/无损)
                                    elif filter_type == '/FlateDecode':
                                        try:
                                            data = obj._data
                                            # 尝试解压并重新压缩
                                            try:
                                                decompressed = zlib.decompress(data)
                                                # 重新压缩,使用更高的压缩级别
                                                recompressed = zlib.compress(decompressed, 9)

                                                if len(recompressed) < len(data):
                                                    obj._data = recompressed
                                                    compressed_count += 1
                                                    if self.verbose:
                                                        reduction = (1 - len(recompressed) / len(data)) * 100
                                                        print(f"    压缩: {len(data)} -> {len(recompressed)} bytes ({reduction:.1f}%)")

                                            except Exception as e:
                                                if self.verbose:
                                                    print(f"    FlateDecode处理失败: {e}")

                                        except Exception as e:
                                            if self.verbose:
                                                print(f"    PNG处理失败: {e}")

                            except Exception as e:
                                if self.verbose:
                                    print(f"  图片处理失败: {e}")

                writer.add_page(page)

            # 写入压缩后的PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            message = f"激进压缩完成 (处理了 {image_count} 张图片,压缩了 {compressed_count} 张)"
            return True, message

        except Exception as e:
            return False, f"压缩失败: {e}"

    def compress_pdf_with_images(self, input_path: str, output_path: str) -> Tuple[bool, str]:
        """
        带图片压缩的PDF压缩方法

        Args:
            input_path: 输入PDF路径
            output_path: 输出PDF路径

        Returns:
            (成功标志, 消息)
        """
        try:
            # 读取PDF
            reader = PdfReader(input_path)
            writer = PdfWriter()

            # 处理每一页
            for page_num, page in enumerate(reader.pages):
                if self.verbose:
                    print(f"处理第 {page_num + 1} 页...")

                # 尝试压缩页面中的图片
                if '/XObject' in page['/Resources']:
                    x_object = page['/Resources']['/XObject'].get_object()

                    for obj_name in x_object:
                        obj = x_object[obj_name].get_object()

                        # 如果是图片对象
                        if obj.get('/Subtype') == '/Image':
                            try:
                                # 获取图片数据
                                if '/Filter' in obj:
                                    # 处理已压缩的图片
                                    if obj['/Filter'] == '/DCTDecode':
                                        # JPEG图片,尝试重新压缩
                                        if self.verbose:
                                            print(f"  发现JPEG图片: {obj_name}")
                                        # 这里可以添加重新压缩逻辑
                                    elif obj['/Filter'] == '/FlateDecode':
                                        # PNG/其他压缩格式
                                        if self.verbose:
                                            print(f"  发现压缩图片: {obj_name}")
                            except Exception as e:
                                if self.verbose:
                                    print(f"  处理图片失败: {e}")

                writer.add_page(page)

            # 写入压缩后的PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            return True, "图片压缩完成"

        except Exception as e:
            return False, f"压缩失败: {e}"

    def compress(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        method: str = 'basic'
    ) -> Tuple[bool, str, int, int]:
        """
        压缩PDF文件

        Args:
            input_path: 输入PDF路径
            output_path: 输出PDF路径(可选,默认在原文件名后添加_compressed)
            method: 压缩方法 ('basic' 或 'images')

        Returns:
            (成功标志, 消息, 原始大小, 压缩后大小)
        """
        # 检查输入文件
        if not os.path.exists(input_path):
            return False, f"输入文件不存在: {input_path}", 0, 0

        if not input_path.lower().endswith('.pdf'):
            return False, "输入文件不是PDF格式", 0, 0

        # 设置输出路径
        if output_path is None:
            path = Path(input_path)
            output_path = str(path.parent / f"{path.stem}_compressed{path.suffix}")

        # 获取原始文件大小
        original_size = self.get_file_size(input_path)

        if self.verbose:
            print(f"原始文件大小: {self.format_size(original_size)}")
            print(f"压缩方法: {method}")
            print(f"图片质量: {self.quality}")

        # 执行压缩
        if method == 'basic':
            success, message = self.compress_pdf_basic(input_path, output_path)
        elif method == 'images':
            success, message = self.compress_pdf_with_images(input_path, output_path)
        elif method == 'aggressive':
            success, message = self.compress_pdf_aggressive(input_path, output_path)
        else:
            return False, f"未知的压缩方法: {method}", original_size, 0

        if not success:
            return False, message, original_size, 0

        # 获取压缩后文件大小
        compressed_size = self.get_file_size(output_path)

        if self.verbose:
            print(f"压缩后文件大小: {self.format_size(compressed_size)}")
            compression_ratio = (1 - compressed_size / original_size) * 100
            print(f"压缩率: {compression_ratio:.2f}%")

        return True, message, original_size, compressed_size


def batch_compress(
    input_dir: str,
    output_dir: Optional[str] = None,
    quality: int = 85,
    method: str = 'basic',
    verbose: bool = False
) -> None:
    """
    批量压缩目录中的PDF文件

    Args:
        input_dir: 输入目录
        output_dir: 输出目录(可选)
        quality: 图片质量
        method: 压缩方法
        verbose: 是否显示详细信息
    """
    if not os.path.isdir(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}")
        return

    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.join(input_dir, 'compressed')

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 查找所有PDF文件
    pdf_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"在目录 {input_dir} 中未找到PDF文件")
        return

    print(f"找到 {len(pdf_files)} 个PDF文件")

    # 创建压缩器
    compressor = PDFCompressor(quality=quality, verbose=verbose)

    # 压缩每个文件
    success_count = 0
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] 处理: {os.path.basename(pdf_file)}")

        # 设置输出路径
        output_file = os.path.join(
            output_dir,
            f"{Path(pdf_file).stem}_compressed.pdf"
        )

        # 压缩
        success, message, orig_size, comp_size = compressor.compress(
            pdf_file, output_file, method
        )

        if success:
            success_count += 1
            ratio = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0
            print(f"✓ {message}")
            print(f"  {compressor.format_size(orig_size)} -> {compressor.format_size(comp_size)} ({ratio:.2f}%)")
        else:
            print(f"✗ {message}")

    print(f"\n完成! 成功压缩 {success_count}/{len(pdf_files)} 个文件")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='PDF压缩工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 压缩单个PDF文件
  python pdf_compressor.py input.pdf

  # 指定输出文件
  python pdf_compressor.py input.pdf -o output.pdf

  # 设置图片质量(1-100)
  python pdf_compressor.py input.pdf -q 70

  # 使用图片压缩方法
  python pdf_compressor.py input.pdf -m images

  # 批量压缩目录中的PDF
  python pdf_compressor.py -d /path/to/pdfs

  # 批量压缩并指定输出目录
  python pdf_compressor.py -d /path/to/pdfs -o /path/to/output
        """
    )

    parser.add_argument('input', nargs='?', help='输入PDF文件路径')
    parser.add_argument('-o', '--output', help='输出PDF文件路径')
    parser.add_argument('-d', '--dir', help='批量处理目录')
    parser.add_argument('-q', '--quality', type=int, default=85,
                       help='图片压缩质量 (1-100, 默认85)')
    parser.add_argument('-m', '--method', choices=['basic', 'images', 'aggressive'],
                       default='aggressive', help='压缩方法 (basic/images/aggressive, 默认aggressive)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='显示详细信息')

    args = parser.parse_args()

    # 检查参数
    if not args.input and not args.dir:
        parser.print_help()
        sys.exit(1)

    # 批量处理
    if args.dir:
        batch_compress(
            args.dir,
            args.output,
            args.quality,
            args.method,
            args.verbose
        )
        return

    # 单文件处理
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        sys.exit(1)

    # 创建压缩器
    compressor = PDFCompressor(quality=args.quality, verbose=args.verbose)

    # 压缩
    success, message, orig_size, comp_size = compressor.compress(
        args.input, args.output, args.method
    )

    if success:
        print(f"\n✓ {message}")
        print(f"原始大小: {compressor.format_size(orig_size)}")
        print(f"压缩后大小: {compressor.format_size(comp_size)}")
        if orig_size > 0:
            ratio = (1 - comp_size / orig_size) * 100
            print(f"压缩率: {ratio:.2f}%")

        # 显示输出路径
        if args.output:
            output_path = args.output
        else:
            path = Path(args.input)
            output_path = str(path.parent / f"{path.stem}_compressed{path.suffix}")
        print(f"输出文件: {output_path}")
    else:
        print(f"\n✗ {message}")
        sys.exit(1)


if __name__ == '__main__':
    main()
