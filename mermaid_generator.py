"""
Mermaid流程图生成模块
根据子系统和协作关系生成mermaid流程图
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from LLMTool import LLMApiClient
from common_utils import LogUtils, JSONProcessor

class MermaidGenerator:
    """Mermaid流程图生成器类"""
    
    def __init__(self):
        self.llm_client = LLMApiClient()
        LogUtils.log_info("Mermaid流程图生成器初始化完成")
    
    def _load_mermaid_prompt_template(self) -> str:
        """
        加载生成mermaid的提示词模板
        
        Returns:
            mermaid生成提示词模板内容
        """
        return """prompt MERMAID{
@Persona {
您是一名专业的流程图设计师和系统架构师，擅长将复杂的系统协作关系转换为清晰的可视化流程图。
}
@Description {
您的角色是：根据子系统列表和协作关系描述，生成清晰、美观的mermaid流程图代码。
}
@ContextControl {
@Rules {
1. 必须输出完整的 mermaid 流程图代码，使用 flowchart TD 格式。
2. 根据子系统的实现方式进行差异化显示：
   - 代码实现的子系统使用矩形节点 [子系统名称-CODE]
   - CNLP实现的子系统使用圆角矩形节点 (子系统名称-CNLP)
3. 节点ID使用简洁的标识符（如A、B、C等），标签显示完整名称。
4. 根据协作关系描述添加合适的箭头和连接。
5. 添加适当的样式类以区分不同类型的子系统。
6. 确保流程图逻辑清晰，从输入到输出有明确的流向。
7. 输出必须是完整可用的 mermaid 代码，包裹在 ```mermaid ``` 代码块中。
8. 不要输出解释性文字，只输出 mermaid 代码。
}
}
@Instruction Split prompt and order {
@InputVariable {
子系统列表: {subsystems}
协作关系: {collaboration}
}
@Commands {
step1: 分析子系统列表，识别每个子系统的名称和实现方式（代码/CNLP）。
step2: 分析协作关系描述，提取子系统间的流程顺序和依赖关系。
step3: 设计流程图结构，确定节点类型和连接关系。
step4: 生成 mermaid 流程图代码，包含节点定义、连接关系和样式。
step5: 添加样式类定义，区分代码实现和CNLP实现的子系统。
}
@OutputVariable {
```mermaid
flowchart TD
    %% 节点定义
    A[子系统1-CODE]
    B(子系统2-CNLP)
    
    %% 连接关系
    A --> B
    
    %% 样式定义
    classDef codeSystem fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef cnlpSystem fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    
    %% 应用样式
    class A codeSystem
    class B cnlpSystem
```
}
}
@Format {
输出严格遵循 mermaid 代码块格式，确保语法正确。
}
}"""
    
    def generate_mermaid_diagram(self, subsystems_data: Dict[str, Any], quiet: bool = False) -> Optional[str]:
        """
        根据子系统数据生成mermaid流程图
        
        Args:
            subsystems_data: 包含subsystems和collaboration字段的数据
            quiet: 是否使用安静模式
            
        Returns:
            生成的mermaid代码
        """
        if not quiet:
            LogUtils.log_info("开始生成mermaid流程图...")
        
        try:
            # 提取子系统列表和协作关系
            subsystems = subsystems_data.get("subsystems", [])
            collaboration = subsystems_data.get("collaboration", "")
            
            if not subsystems:
                if not quiet:
                    LogUtils.log_warning("没有找到子系统数据")
                return None
            
            if not collaboration:
                if not quiet:
                    LogUtils.log_warning("没有找到协作关系描述，生成默认描述")
                
                # 生成默认的协作关系描述
                subsystem_names = [s.get("name", f"子系统{i+1}") for i, s in enumerate(subsystems)]
                if len(subsystem_names) <= 1:
                    collaboration = f"单个子系统 {subsystem_names[0] if subsystem_names else '未命名子系统'} 独立处理用户请求"
                else:
                    collaboration = f"系统按顺序执行：{' → '.join(subsystem_names)}，每个子系统处理特定的业务逻辑"
                
                if not quiet:
                    LogUtils.log_info(f"使用默认协作关系: {collaboration}")
            
            # 准备子系统信息
            subsystem_info = self._prepare_subsystem_info(subsystems)
            
            # 构建输入内容
            input_content = f"子系统列表: {json.dumps(subsystem_info, ensure_ascii=False)}\n协作关系: {collaboration}"
            
            # 获取提示词模板
            mermaid_prompt = self._load_mermaid_prompt_template()
            
            # 替换模板中的占位符
            mermaid_prompt = mermaid_prompt.replace("{subsystems}", json.dumps(subsystem_info, ensure_ascii=False))
            mermaid_prompt = mermaid_prompt.replace("{collaboration}", collaboration)
            
            messages = [
                {"role": "system", "content": mermaid_prompt},
                {"role": "user", "content": ""}
            ]
            
            response = self.llm_client.call(messages)
            if not response:
                if not quiet:
                    LogUtils.log_error("LLM调用失败")
                return None
            
            # 提取mermaid代码
            mermaid_code = self._extract_mermaid_code(response)
            if mermaid_code:
                if not quiet:
                    LogUtils.log_success("mermaid流程图生成完成")
                return mermaid_code
            else:
                if not quiet:
                    LogUtils.log_warning("未找到有效的mermaid代码")
                return None
                
        except Exception as e:
            if not quiet:
                LogUtils.log_error(f"mermaid流程图生成失败: {e}")
            return None
    
    def _prepare_subsystem_info(self, subsystems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        准备子系统信息，标识每个子系统的实现方式
        
        Args:
            subsystems: 原始子系统列表
            
        Returns:
            包含实现方式标识的子系统信息
        """
        subsystem_info = []
        
        for i, subsystem in enumerate(subsystems):
            name = subsystem.get("name", f"子系统{i+1}")
            
            # 优先使用实际实现结果（如果存在）
            if "actual_implementation" in subsystem:
                implementation_type = subsystem["actual_implementation"]
            else:
                # 回退到基于字段存在性的判断（向后兼容）
                has_code = "code" in subsystem and subsystem["code"]
                has_cnlp = "cnlp" in subsystem and subsystem["cnlp"]
                
                # 只区分CODE和CNLP，不存在混合实现
                if has_code:
                    implementation_type = "CODE"
                else:
                    implementation_type = "CNLP"  # 默认为CNLP
            
            info = {
                "name": name,
                "implementation": implementation_type,
                "description": subsystem.get("description", ""),
                "index": i
            }
            
            subsystem_info.append(info)
        
        return subsystem_info
    
    def _extract_mermaid_code(self, response: str) -> Optional[str]:
        """
        从响应中提取mermaid代码
        
        Args:
            response: LLM响应内容
            
        Returns:
            提取的mermaid代码
        """
        # 查找```mermaid代码块
        mermaid_pattern = r'```mermaid\s*(.*?)\s*```'
        matches = re.findall(mermaid_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 如果没找到，尝试查找普通代码块
        code_pattern = r'```\s*(.*?)\s*```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            # 检查是否包含mermaid关键字
            for match in matches:
                if any(keyword in match.lower() for keyword in ['flowchart', 'graph', 'classDef', '-->']):
                    return match.strip()
        
        return None
    
    def generate_enhanced_mermaid_with_details(self, subsystems_data: Dict[str, Any], include_details: bool = True, quiet: bool = False) -> Optional[str]:
        """
        生成增强版的mermaid流程图，包含更多细节信息
        
        Args:
            subsystems_data: 包含subsystems和collaboration字段的数据
            include_details: 是否包含详细信息（如输入输出）
            quiet: 是否使用安静模式
            
        Returns:
            生成的增强版mermaid代码
        """
        if not quiet:
            LogUtils.log_info("开始生成增强版mermaid流程图...")
        
        try:
            basic_mermaid = self.generate_mermaid_diagram(subsystems_data, quiet=True)
            if not basic_mermaid:
                return None
            
            if not include_details:
                return basic_mermaid
            
            # 添加详细信息的增强处理
            enhanced_mermaid = self._enhance_mermaid_with_io_info(basic_mermaid, subsystems_data.get("subsystems", []))
            
            if not quiet:
                LogUtils.log_success("增强版mermaid流程图生成完成")
            
            return enhanced_mermaid
            
        except Exception as e:
            if not quiet:
                LogUtils.log_error(f"增强版mermaid流程图生成失败: {e}")
            return None
    
    def _enhance_mermaid_with_io_info(self, basic_mermaid: str, subsystems: List[Dict[str, Any]]) -> str:
        """
        为基础mermaid添加输入输出信息
        
        Args:
            basic_mermaid: 基础mermaid代码
            subsystems: 子系统列表
            
        Returns:
            增强后的mermaid代码
        """
        # 这里可以添加输入输出信息的处理逻辑
        # 例如在节点旁边添加输入输出说明
        lines = basic_mermaid.split('\n')
        enhanced_lines = []
        
        for line in lines:
            enhanced_lines.append(line)
            # 在这里可以添加输入输出信息的注释
            # 例如: %% 输入: xxx, 输出: yyy
        
        return '\n'.join(enhanced_lines)
    
    def validate_mermaid_syntax(self, mermaid_code: str) -> Tuple[bool, str]:
        """
        验证mermaid代码的基本语法
        
        Args:
            mermaid_code: mermaid代码
            
        Returns:
            (是否有效, 错误信息)
        """
        if not mermaid_code:
            return False, "mermaid代码为空"
        
        try:
            # 基本语法检查
            if not re.search(r'flowchart|graph', mermaid_code):
                return False, "缺少flowchart或graph声明"
            
            # 检查是否有节点定义
            if not re.search(r'[A-Za-z]+\[.*?\]|[A-Za-z]+\(.*?\)|[A-Za-z]+\{.*?\}', mermaid_code):
                return False, "未找到有效的节点定义"
            
            # 检查是否有连接关系
            if not re.search(r'-->', mermaid_code):
                return False, "未找到连接关系"
            
            return True, "语法验证通过"
            
        except Exception as e:
            return False, f"语法验证异常: {str(e)}"
    
    def save_mermaid_to_file(self, mermaid_code: str, filename: str, output_dir: str = "gen_code/output") -> bool:
        """
        保存mermaid代码到文件
        
        Args:
            mermaid_code: mermaid代码
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            是否保存成功
        """
        try:
            import os
            os.makedirs(output_dir, exist_ok=True)
            
            # 确保文件扩展名正确
            if not filename.endswith('.md'):
                filename += '.md'
            
            filepath = os.path.join(output_dir, filename)
            
            # 构建完整的markdown文件内容
            content = f"""# 系统流程图

```mermaid
{mermaid_code}
```

## 说明
此流程图展示了系统各子系统之间的协作关系：
- 矩形节点 []: 代码实现的子系统
- 圆角矩形节点 (): CNLP实现的子系统  
- 菱形节点 {{}}: 混合实现的子系统
"""
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            LogUtils.log_success(f"mermaid流程图已保存到 {filepath}")
            return True
            
        except Exception as e:
            LogUtils.log_error(f"保存mermaid流程图失败: {e}")
            return False 