import sys
import platform
import subprocess
import os
import glob
import traceback

def docx_to_pdf(input_path, output_path):
    """
    将指定的 docx 文件转换为 pdf 文件
    :param input_path: 输入的 docx 文件路径
    :param output_path: 输出的 pdf 文件路径
    :raises: Exception 转换失败时抛出异常
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    # 检查输出目录是否存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    if platform.system() == "Windows":
        try:
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from docx2pdf import convert
                # 使用 docx2pdf 进行转换
                convert(input_path, output_path)
                
                # 验证输出文件是否生成
                if not os.path.exists(output_path):
                    raise RuntimeError(f"PDF文件生成失败: {output_path}")
                
                print(f"成功将 {input_path} 转换为 {output_path}")
            finally:
                pythoncom.CoUninitialize()
        except ImportError as e:
            raise ImportError(
                f"缺少依赖库: {e}\n"
                "请安装: pip install pythoncom docx2pdf\n"
                "注意: docx2pdf 需要安装 Microsoft Word"
            )
        except Exception as e:
            raise RuntimeError(
                f"PDF转换失败: {e}\n"
                f"详细信息:\n{traceback.format_exc()}\n"
                "可能的原因:\n"
                "1. 未安装 Microsoft Word\n"
                "2. Word 进程被占用\n"
                "3. 文件权限问题\n"
                "4. COM 接口初始化失败"
            )
    else:
        try:
            # 检查 libreoffice 是否安装
            result = subprocess.run(
                ["which", "libreoffice"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "未找到 libreoffice 命令\n"
                    "请安装: sudo apt install libreoffice"
                )
            
            # 使用 libreoffice 进行转换
            result = subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf", 
                 input_path, "--outdir", output_dir],
                capture_output=True,
                text=True,
                timeout=60  # 添加超时限制
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice 转换失败:\n"
                    f"返回码: {result.returncode}\n"
                    f"错误输出: {result.stderr}"
                )
            
            # 验证输出文件是否生成
            if not os.path.exists(output_path):
                raise RuntimeError(f"PDF文件生成失败: {output_path}")
            
            print(f"成功将 {input_path} 转换为 {output_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice 转换超时（60秒）")
        except Exception as e:
            raise RuntimeError(
                f"PDF转换失败: {e}\n"
                f"详细信息:\n{traceback.format_exc()}"
            )

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python docx2pdf.py <input.docx> <output.pdf>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    docx_to_pdf(input_file, output_file)