"""
基础需求收集与校验子系统 - 自动生成的代码
原始需求: {'name': '基础需求收集与校验子系统', 'contained_modules': ['A[读取聊天信息]', 'I[审核基础需求信息]', 'J[内容方向/账号类型可映射?]', 'K[提示...
"""

def collect_basic_requirements(chat_input: str, user_classes: list = None, existing_requirements: dict = None) -> tuple:
    """基础需求收集与校验子系统主函数"""
    # 初始化需求字典（修复非字典类型existing_requirements的copy问题）
    if isinstance(existing_requirements, dict):
        collected_requirements = existing_requirements.copy()
    else:
        collected_requirements = {}
    
    # 模块J: 字段映射配置
    FIELD_MAPPING = {
        "内容方向": "content_direction",
        "账号类型": "account_type",
        "用户类别": "user_class",
    }
    
    # 模块I: 必填字段配置
    REQUIRED_FIELDS = ["content_direction", "account_type", "user_class"]
    
    try:
        # 模块A: 读取聊天输入
        chat_content = chat_input.strip() if isinstance(chat_input, str) else ""
        
        # 解析输入字段
        parsed_fields = {}
        for item in chat_content.split(','):
            if ':' in item:
                key, value = item.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key in FIELD_MAPPING:
                    parsed_fields[FIELD_MAPPING[key]] = value
        
        # 模块P: 更新需求字典（确保collected_requirements是字典类型）
        if isinstance(collected_requirements, dict):
            collected_requirements.update(parsed_fields)
        else:
            collected_requirements = parsed_fields.copy()
        
        # 模块L: 检查缺失字段
        missing_fields = [field for field in REQUIRED_FIELDS if field not in collected_requirements]
        
        # 模块M: 生成补充提示
        if missing_fields:
            reverse_mapping = {v: k for k, v in FIELD_MAPPING.items()}
            readable_fields = [reverse_mapping.get(field, field) for field in missing_fields]
            prompt = f"请补充以下信息: {', '.join(readable_fields)}"
            
            # 模块K: 用户类别选择提示
            if "user_class" in missing_fields and isinstance(user_classes, list):
                prompt += f"。用户类别可选: {', '.join(user_classes)}"
                
            return (False, ['MissingFields'], prompt)
        else:
            # 所有必填字段已收集
            return (True, [], collected_requirements)
            
    except ValueError as e:
        return (False, ['ValueError'], f"处理错误: {str(e)}")
    except Exception as e:
        return (False, [type(e).__name__], f"处理错误: {str(e)}")
