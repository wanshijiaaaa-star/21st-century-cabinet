# -*- coding: UTF-8 -*-
import base64
import binascii
import os
from typing import Optional
def base64_encode(data: str) -> str:
    """
    Base64编码函数
    
    Args:
        data: 需要编码的字符串
        
    Returns:
        Base64编码后的字符串
    """
    if not data:
        return ""
    
    # 将字符串转换为bytes
    data_bytes = data.encode('utf-8')
    
    # 进行base64编码
    encoded_bytes = base64.b64encode(data_bytes)
    
    # 将bytes转换为字符串
    return encoded_bytes.decode('utf-8')


def base64_decode(encoded_data: str) -> str:
    """
    Base64解码函数
    
    Args:
        encoded_data: Base64编码的字符串
        
    Returns:
        解码后的原始字符串
        
    Raises:
        binascii.Error: 如果输入不是有效的base64编码
    """
    if not encoded_data:
        return ""
    
    try:
        # 将字符串转换为bytes
        encoded_bytes = encoded_data.encode('utf-8')
        
        # 进行base64解码
        decoded_bytes = base64.b64decode(encoded_bytes)
        
        # 将bytes转换为字符串
        return decoded_bytes.decode('utf-8')
    except binascii.Error as e:
        raise ValueError(f"无效的base64编码: {e}")


def base64_encode_bytes(data: bytes) -> bytes:
    """
    Base64编码函数（字节版本）
    
    Args:
        data: 需要编码的字节数据
        
    Returns:
        Base64编码后的字节数据
    """
    if not data:
        return b""
    
    return base64.b64encode(data)


def base64_decode_bytes(encoded_data: bytes) -> bytes:
    """
    Base64解码函数（字节版本）
    
    Args:
        encoded_data: Base64编码的字节数据
        
    Returns:
        解码后的原始字节数据
        
    Raises:
        binascii.Error: 如果输入不是有效的base64编码
    """
    if not encoded_data:
        return b""
    
    try:
        return base64.b64decode(encoded_data)
    except binascii.Error as e:
        raise ValueError(f"无效的base64编码: {e}")


def base64_url_safe_encode(data: str) -> str:
    """
    URL安全的Base64编码函数
    
    Args:
        data: 需要编码的字符串
        
    Returns:
        URL安全的Base64编码字符串（+和/被替换为-和_）
    """
    if not data:
        return ""
    
    # 标准base64编码
    standard_encoded = base64_encode(data)
    
    # 转换为URL安全格式
    url_safe = standard_encoded.replace('+', '-').replace('/', '_').rstrip('=')
    
    return url_safe


def base64_url_safe_decode(encoded_data: str) -> str:
    """
    URL安全的Base64解码函数
    
    Args:
        encoded_data: URL安全的Base64编码字符串
        
    Returns:
        解码后的原始字符串
        
    Raises:
        binascii.Error: 如果输入不是有效的base64编码
    """
    if not encoded_data:
        return ""
    
    # 恢复为标准base64格式
    # 添加填充字符
    padding_needed = len(encoded_data) % 4
    if padding_needed:
        encoded_data += '=' * (4 - padding_needed)
    
    # 替换回标准字符
    standard_encoded = encoded_data.replace('-', '+').replace('_', '/')
    
    # 使用标准解码
    return base64_decode(standard_encoded)


def image_to_base64(image_path: str, mime_type: Optional[str] = None) -> str:
    """
    将图像文件转换为Base64编码字符串
    
    Args:
        image_path: 图像文件的路径
        mime_type: 可选的MIME类型，如果不提供则根据文件扩展名自动判断
        
    Returns:
        Base64编码的图像字符串，格式为 data:image/[type];base64,[data]
        
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是有效的图像文件
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    # 根据文件扩展名确定MIME类型（如果未提供）
    if mime_type is None:
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon'
        }
        mime_type = mime_map.get(ext, 'image/jpeg')  # 默认使用jpeg
    
    try:
        # 读取图像文件并进行base64编码
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
        # 返回data URL格式的base64字符串
        return f"data:{mime_type};base64,{base64_data}"
        
    except Exception as e:
        raise ValueError(f"图像文件处理失败: {e}")


def image_to_base64_data(image_path: str) -> str:
    """
    将图像文件转换为纯Base64编码数据（不包含data URL前缀）
    
    Args:
        image_path: 图像文件的路径
        
    Returns:
        纯Base64编码的图像数据字符串
        
    Raises:
        FileNotFoundError: 如果文件不存在
        ValueError: 如果文件不是有效的图像文件
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return base64_data
            
    except Exception as e:
        raise ValueError(f"图像文件处理失败: {e}")


def base64_to_image(base64_data: str, output_path: str, is_data_url: bool = True) -> None:
    """
    将Base64编码的图像数据保存为图像文件
    
    Args:
        base64_data: Base64编码的图像数据
        output_path: 输出图像文件的路径
        is_data_url: 是否为data URL格式（包含data:image/...前缀）
        
    Raises:
        ValueError: 如果base64数据无效
        OSError: 如果文件写入失败
    """
    try:
        # 如果是data URL格式，提取base64部分
        if is_data_url and base64_data.startswith('data:'):
            # 查找逗号位置，base64数据在逗号之后
            comma_index = base64_data.find(',')
            if comma_index == -1:
                raise ValueError("无效的data URL格式")
            base64_data = base64_data[comma_index + 1:]
        
        # 解码base64数据
        image_data = base64.b64decode(base64_data)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 写入文件
        with open(output_path, 'wb') as image_file:
            image_file.write(image_data)
            
    except Exception as e:
        if "Invalid base64" in str(e):
            raise ValueError(f"无效的base64数据: {e}")
        else:
            raise OSError(f"文件写入失败: {e}")


if __name__ == "__main__":
    # 测试代码
    test_string = "Hello, World!"
    print(base64_encode(test_string))
    
    # # 测试标准base64编码
    # encoded = base64_encode(test_string)
    # print(f"原始字符串: {test_string}")
    # print(f"Base64编码: {encoded}")
    
    # # 测试解码
    # decoded = base64_decode(encoded)
    # print(f"Base64解码: {decoded}")
    
    # # 测试URL安全编码
    # url_encoded = base64_url_safe_encode(test_string)
    # print(f"URL安全Base64编码: {url_encoded}")
    
    # # 测试URL安全解码
    # url_decoded = base64_url_safe_decode(url_encoded)
    # print(f"URL安全Base64解码: {url_decoded}")
    
    # # 验证结果
    # assert test_string == decoded == url_decoded, "编解码测试失败"
    # print("所有测试通过！")
    
    # # 测试图像转base64功能
    # try:
    #     # 测试图像转base64（需要一个实际存在的图像文件）
    #     # image_path = "test_image.jpg"  # 替换为实际图像路径
    #     # if os.path.exists(image_path):
    #     #     # 测试带data URL前缀的转换
    #     #     base64_image = image_to_base64(image_path)
    #     #     print(f"图像Base64 (前100字符): {base64_image[:100]}...")
    #     
    #     #     # 测试纯base64数据转换
    #     #     base64_data = image_to_base64_data(image_path)
    #     #     print(f"纯Base64数据 (前50字符): {base64_data[:50]}...")
    #     
    #     #     # 测试base64转图像
    #     #     output_path = "output_image.jpg"
    #     #     base64_to_image(base64_image, output_path)
    #     #     print(f"Base64数据已保存为图像: {output_path}")
    #     # else:
    #     #     print("测试图像文件不存在，跳过图像测试")
    #     
    # except Exception as e:
    #     print(f"图像测试失败: {e}")