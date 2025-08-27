"""
PromptSplit 公共工具模块
整合项目中的重复代码，提供统一的工具函数
"""

import json
import re
import os
from typing import List, Dict, Any, Optional


class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def read_file(file_path: str, encoding: str = 'utf-8') -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            encoding: 文件编码，默认utf-8
            
        Returns:
            文件内容字符串，读取失败返回空字符串
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ 文件 {file_path} 不存在")
            return ""
        except Exception as e:
            print(f"❌ 读取文件 {file_path} 时出错: {e}")
            return ""
    
    @staticmethod
    def save_file(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
        """
        保存文件内容
        
        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码，默认utf-8
            
        Returns:
            是否保存成功
        """
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            print(f"✅ 已保存到 {file_path}")
            return True
        except Exception as e:
            print(f"❌ 保存文件 {file_path} 时出错: {e}")
            return False
    
    @staticmethod
    def save_json(file_path: str, data: Dict, encoding: str = 'utf-8') -> bool:
        """
        保存JSON数据
        
        Args:
            file_path: 文件路径
            data: 要保存的数据
            encoding: 文件编码，默认utf-8
            
        Returns:
            是否保存成功
        """
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存JSON到 {file_path}")
            return True
        except Exception as e:
            print(f"❌ 保存JSON文件 {file_path} 时出错: {e}")
            return False


class TextProcessor:
    """文本处理工具类"""
    
    @staticmethod
    def split_text_by_length(text: str, chunk_size: int = 500) -> List[str]:
        """
        根据指定长度切割文本，确保在换行符或段落边界切割
        
        Args:
            text: 待切割的原始文本
            chunk_size: 每段文本的最小长度，默认500
            
        Returns:
            切割后的文本段列表
            
        Raises:
            TypeError: 输入不是字符串类型
            ValueError: chunk_size不是正数
        """
        if not isinstance(text, str):
            raise TypeError("输入必须是字符串类型")
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须为正数")
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            if end < text_length:
                # 向后寻找段落分隔符
                next_paragraph_break = text.find('\n\n', end)
                if next_paragraph_break != -1:
                    end = next_paragraph_break + 2
                else:
                    # 寻找换行符
                    next_newline = text.find('\n', end)
                    if next_newline != -1:
                        end = next_newline + 1
                    else:
                        end = text_length
            
            chunks.append(text[start:end])
            start = end
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本，移除多余的空白字符
        
        Args:
            text: 待清理的文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除多余的空白行
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        # 移除行尾空白
        text = re.sub(r'[ \t]+\n', '\n', text)
        # 移除开头和结尾的空白
        text = text.strip()
        
        return text


class JSONProcessor:
    """JSON处理工具类"""
    
    @staticmethod
    def extract_json_string(text: str) -> str:
        """
        从文本中提取JSON字符串
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            提取的JSON字符串，如果未找到则返回原文本
        """
        if not text:
            return ""
        
        # 尝试匹配不同的JSON模式
        patterns = [
            r'\{(?:[^{}]|{[^{}]*})*\}',  # 匹配对象
            r'\[(?:[^\[\]]|\[[^\[\]]*\])*\]',  # 匹配数组
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                # 返回最长的匹配项
                return max(matches, key=len)
        
        return text
    
    @staticmethod
    def extract_variables_from_json(json_str: str) -> List[str]:
        """
        从LLM返回的JSON字符串中提取变量名
        
        Args:
            json_str: LLM响应的JSON字符串
            
        Returns:
            提取到的变量名列表
        """
        if not json_str:
            return []
        
        # 首先尝试提取JSON数组部分
        match = re.search(r'\[.*?\]', json_str, re.DOTALL)
        if not match:
            return []
        
        try:
            json_array = json.loads(match.group(0))
            variable_names = [
                item['text'] for item in json_array 
                if isinstance(item, dict) and 'text' in item
            ]
            return variable_names
        except json.JSONDecodeError as e:
            print(f"解析JSON失败: {e}")
            return []
    
    @staticmethod
    def safe_json_loads(json_str: str) -> Optional[Dict]:
        """
        安全地加载JSON字符串
        
        Args:
            json_str: JSON字符串
            
        Returns:
            解析后的字典，失败返回None
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None


class ValidationUtils:
    """验证工具类"""
    
    @staticmethod
    def validate_file_exists(file_path: str) -> bool:
        """
        验证文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否存在
        """
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    @staticmethod
    def validate_directory_exists(dir_path: str) -> bool:
        """
        验证目录是否存在
        
        Args:
            dir_path: 目录路径
            
        Returns:
            目录是否存在
        """
        return os.path.exists(dir_path) and os.path.isdir(dir_path)
    
    @staticmethod
    def validate_chunk_size(chunk_size: int) -> bool:
        """
        验证分块大小是否有效
        
        Args:
            chunk_size: 分块大小
            
        Returns:
            是否有效
        """
        return isinstance(chunk_size, int) and chunk_size > 0
    
    @staticmethod
    def validate_text_input(text: str) -> bool:
        """
        验证文本输入是否有效
        
        Args:
            text: 文本内容
            
        Returns:
            是否有效
        """
        return isinstance(text, str) and len(text.strip()) > 0


class LogUtils:
    """日志工具类"""
    
    @staticmethod
    def log_step(step_name: str, message: str = ""):
        """
        记录步骤日志
        
        Args:
            step_name: 步骤名称
            message: 附加消息
        """
        separator = "=" * 50
        print(f"{separator}")
        print(f"🔄 {step_name}")
        if message:
            print(f"📝 {message}")
    
    @staticmethod
    def log_success(message: str):
        """记录成功日志"""
        print(f"✅ {message}")
    
    @staticmethod
    def log_warning(message: str):
        """记录警告日志"""
        print(f"⚠️ {message}")
    
    @staticmethod
    def log_error(message: str):
        """记录错误日志"""
        print(f"❌ {message}")
    
    @staticmethod
    def log_info(message: str):
        """记录信息日志"""
        print(f"ℹ️ {message}")


class ConfigUtils:
    """配置工具类"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'chunk_size': 500,
        'max_workers': 5,
        'api_timeout': 30,
        'encoding': 'utf-8',
        'output_dir': 'output'
    }
    
    @staticmethod
    def get_config(config_file: str = 'config.json') -> Dict[str, Any]:
        """
        获取配置
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        if ValidationUtils.validate_file_exists(config_file):
            config_content = FileUtils.read_file(config_file)
            config = JSONProcessor.safe_json_loads(config_content)
            if config:
                # 合并默认配置
                merged_config = ConfigUtils.DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
        
        return ConfigUtils.DEFAULT_CONFIG.copy()
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_file: str = 'config.json') -> bool:
        """
        保存配置
        
        Args:
            config: 配置字典
            config_file: 配置文件路径
            
        Returns:
            是否保存成功
        """
        return FileUtils.save_json(config_file, config)


# 便捷导入
__all__ = [
    'FileUtils',
    'TextProcessor', 
    'JSONProcessor',
    'ValidationUtils',
    'LogUtils',
    'ConfigUtils'
] 