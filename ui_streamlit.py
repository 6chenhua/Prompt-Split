"""
AI提示词智能拆分工具 - Streamlit Web界面
提供现代化的Web界面，支持实时进度显示和结果可视化
"""
from urllib.parse import urlparse

import streamlit as st
import time
import json
import os
from typing import Dict, Any, Optional, Callable
import threading
from pathlib import Path

# 设置页面配置
st.set_page_config(
    page_title="AI提示词智能拆分工具",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式
st.markdown("""
<style>
/* 主标题样式 */
.main-title {
    text-align: center;
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    margin-bottom: 2rem;
    padding: 1rem;
    background: linear-gradient(90deg, #e3f2fd, #ffffff, #e3f2fd);
    border-radius: 10px;
    border: 2px solid #1f77b4;
}

/* 步骤卡片样式 */
.step-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 10px;
    border-left: 4px solid #28a745;
    margin: 0.5rem 0;
}

.step-card.active {
    background: #e7f3ff;
    border-left-color: #007bff;
}

.step-card.completed {
    background: #d4edda;
    border-left-color: #28a745;
}

.step-card.error {
    background: #f8d7da;
    border-left-color: #dc3545;
}

/* 结果展示区域 */
.result-container {
    background: #ffffff;
    padding: 1.5rem;
    border-radius: 15px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin: 1rem 0;
}

/* 成功提示 */
.success-box {
    background: #d4edda;
    color: #155724;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #c3e6cb;
    margin: 1rem 0;
}

/* 错误提示 */
.error-box {
    background: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #f5c6cb;
    margin: 1rem 0;
}

/* 统计信息卡片 */
.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
    margin: 0.5rem;
}

.stat-number {
    font-size: 2rem;
    font-weight: bold;
}

.stat-label {
    font-size: 0.9rem;
    opacity: 0.9;
}
</style>
""", unsafe_allow_html=True)


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置进度"""
        self.steps = [
            {"name": "输入验证", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "🔍"},
            {"name": "文本分块", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "✂️"},
            {"name": "提取变量", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "🔤"},
            {"name": "后处理变量", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "🔧"},
            {"name": "生成Mermaid图", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "🎨"},
            {"name": "拆分子系统", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "🧩"},
            {"name": "生成子提示词", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "📝"},
            {"name": "代码生成", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "💻"},
            {"name": "转换CNLP", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "🔄"},
            {"name": "整合结果", "status": "pending", "message": "", "progress": 0, "result": None, "icon": "📋"}
        ]
        self.current_step = 0
        self.overall_progress = 0
        self.logs = []
        self.result = None
        self.error = None
        self.processing_complete = False
        self.has_error = False
        self.start_time = None  # 添加开始时间记录
    
    def start_step(self, step_index: int, message: str = ""):
        """开始某个步骤"""
        if 0 <= step_index < len(self.steps):
            # 记录开始时间（第一个步骤）
            if self.start_time is None:
                import time
                self.start_time = time.time()
            
            self.current_step = step_index
            self.steps[step_index]["status"] = "active"
            self.steps[step_index]["message"] = message
            self.logs.append(f"🔄 {self.steps[step_index]['name']}: {message}")
    
    def complete_step(self, step_index: int, message: str = "完成", result_data: Any = None):
        """完成某个步骤"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "completed"
            self.steps[step_index]["message"] = message
            self.steps[step_index]["progress"] = 100
            self.steps[step_index]["result"] = result_data
            self.overall_progress = min(100, (step_index + 1) * (100 / len(self.steps)))
            self.logs.append(f"✅ {self.steps[step_index]['name']}: {message}")
    
    def error_step(self, step_index: int, error_message: str):
        """步骤出错"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = "error"
            self.steps[step_index]["message"] = error_message
            self.error = error_message
            self.logs.append(f"❌ {self.steps[step_index]['name']}: {error_message}")
    
    def update_step_progress(self, step_index: int, progress: int, message: str = "", result_data: Any = None):
        """更新步骤进度"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["progress"] = progress
            if message:
                self.steps[step_index]["message"] = message
            if result_data is not None:
                self.steps[step_index]["result"] = result_data


def initialize_session_state():
    """初始化会话状态"""
    if "progress_tracker" not in st.session_state:
        st.session_state.progress_tracker = ProgressTracker()
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "result_data" not in st.session_state:
        st.session_state.result_data = None


def render_header():
    """渲染页面头部"""
    st.markdown("""
    <div class="main-title">
        🤖 AI提示词智能拆分工具
        <div style="font-size: 1rem; margin-top: 0.5rem; font-weight: normal;">
            智能提取变量 • 系统化拆分 • CNLP结构化转换
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_input_section():
    """渲染输入区域"""
    st.header("📝 输入配置")
    
    # API配置区域
    render_api_config_section()
    
    st.markdown("---")
    
    # 输入方式选择
    input_method = st.radio(
        "选择输入方式：",
        ["文本输入", "文件上传"],
        horizontal=True
    )
    
    input_text = ""
    
    if input_method == "文本输入":
        input_text = st.text_area(
            "请输入需要拆分的提示词：",
            height=200,
            placeholder="请输入您的AI提示词内容...\n\n示例：你是一个专业的变量抽取器，负责从用户提供的文本中识别出所有可能的变量..."
        )
    else:
        uploaded_file = st.file_uploader(
            "选择文本文件",
            type=['txt', 'md'],
            help="支持.txt和.md文件格式"
        )
        
        if uploaded_file is not None:
            try:
                input_text = str(uploaded_file.read(), "utf-8")
                st.success(f"✅ 文件上传成功！内容长度：{len(input_text)} 字符")
                with st.expander("📄 文件内容预览"):
                    st.text(input_text[:500] + "..." if len(input_text) > 500 else input_text)
            except Exception as e:
                st.error(f"❌ 文件读取失败：{e}")
    
    # 处理配置
    st.subheader("⚙️ 处理配置")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        chunk_size = st.number_input("分块大小", min_value=100, max_value=2000, value=500, step=50)
    with col2:
        max_workers = st.number_input("并发数", min_value=1, max_value=10, value=5, step=1)
    with col3:
        show_debug = st.checkbox("显示详细日志", value=False)
    
    return input_text, chunk_size, max_workers, show_debug


def render_api_config_section():
    """渲染API配置区域"""
    st.subheader("🔑 API配置")
    
    # 检查是否已有API key配置
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'api_config_expanded' not in st.session_state:
        st.session_state.api_config_expanded = not st.session_state.api_key
    
    # API状态显示
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.session_state.api_key:
            masked_key = st.session_state.api_key[:8] + "*" * (len(st.session_state.api_key) - 12) + st.session_state.api_key[-4:]
            st.success(f"✅ API Key已配置: {masked_key}")
        else:
            st.warning("⚠️ 请配置您的API Key以开始使用")
    
    with col2:
        if st.button("🔧 配置API", type="secondary"):
            st.session_state.api_config_expanded = not st.session_state.api_config_expanded
            st.rerun()
    
    # API配置表单
    if st.session_state.api_config_expanded:
        with st.expander("🔑 API Key配置", expanded=True):
            st.markdown("""
            **支持的AI服务商：**
            - Claude (Anthropic)
            - GPT (OpenAI)
            - 其他兼容OpenAI API的服务
            
            **如何获取API Key：**
            1. **Claude**: 访问 [console.anthropic.com](https://console.anthropic.com) 注册并获取API Key
            2. **OpenAI**: 访问 [platform.openai.com](https://platform.openai.com) 注册并获取API Key
            3. **其他服务**: 查看相应服务商的文档
            """)
            
            # API Key输入
            api_key_input = st.text_input(
                "API Key",
                value=st.session_state.api_key,
                type="password",
                placeholder="请输入您的API Key (如: sk-ant-api03-...)",
                help="您的API Key将仅在本次会话中使用，不会被存储"
            )
            
            # API服务配置
            col1, col2 = st.columns(2)
            
            with col1:
                api_base_url = st.text_input(
                    "API Base URL",
                    value=st.session_state.get('api_base_url', 'https://api.rcouyi.com'),
                    placeholder="https://api.rcouyi.com",
                    help="API服务的基础URL"
                )
            
            with col2:
                api_model = st.selectbox(
                    "模型选择",
                    ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-5-mini", "gpt-5", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                    index=0,
                    help="选择要使用的AI模型"
                )
            
            # 保存按钮
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("💾 保存配置", type="primary"):
                    if api_key_input.strip():
                        st.session_state.api_key = api_key_input.strip()
                        st.session_state.api_base_url = api_base_url.strip()
                        st.session_state.api_model = api_model
                        st.session_state.api_config_expanded = False
                        
                        # 更新配置文件
                        update_api_config(api_key_input.strip(), api_base_url.strip(), api_model)
                        
                        st.success("✅ API配置已保存")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 请输入有效的API Key")
            
            with col2:
                if st.button("🧪 测试连接"):
                    if api_key_input.strip():
                        with st.spinner("测试API连接..."):
                            test_result = test_api_connection(api_key_input.strip(), api_base_url.strip(), api_model)
                            if test_result["success"]:
                                st.success(f"✅ {test_result['message']}")
                            else:
                                st.error(f"❌ {test_result['message']}")
                    else:
                        st.error("❌ 请先输入API Key")
            
            with col3:
                st.markdown("""
                <div style="background-color: #f0f2f6; padding: 0.5rem; border-radius: 0.5rem; font-size: 0.8rem;">
                <strong>💡 安全提示:</strong><br>
                • API Key仅在浏览器会话中使用<br>
                • 不会上传到服务器或永久存储<br>
                • 关闭浏览器后需要重新输入
                </div>
                """, unsafe_allow_html=True)


def update_api_config(api_key: str, base_url: str, model: str):
    """更新API配置到config.json"""
    try:
        from common_utils import ConfigUtils
        
        # 读取现有配置
        config = ConfigUtils.get_config()
        
        # 更新API配置
        if 'api' not in config:
            config['api'] = {}
        
        # 只更新URL和模型，不存储API Key（安全考虑）
        config['api']['url'] = base_url
        config['api']['model'] = model
        
        # 保存配置
        ConfigUtils.save_config(config)
        
    except Exception as e:
        st.warning(f"⚠️ 配置保存失败: {e}")


def setup_user_api_config(api_key: str, base_url: str, model: str):
    """设置用户的API配置"""
    try:
        from LLMTool import LLMApiClient
        
        # 获取全局LLM客户端实例并更新配置
        import first_spilit
        if hasattr(first_spilit, 'llm_client'):
            # 验证API key不为空
            if not api_key or not api_key.strip():
                st.error(" API Key不能为空，请输入有效的API Key")
                return
            
            first_spilit.llm_client.api_key = api_key
            if base_url:
                # 解析URL设置host和path
                first_spilit.llm_client.api_key = api_key.strip()
                parsed = urlparse(base_url)
                first_spilit.llm_client.host = parsed.netloc
                
                # 根据不同的API服务设置正确的路径
                if "anthropic" in base_url.lower():
                    first_spilit.llm_client.path = "/v1/messages"
                elif "openai" in base_url.lower() or "rcouyi" in base_url.lower():
                    first_spilit.llm_client.path = "/v1/chat/completions"
                else:
                    # 默认尝试OpenAI兼容格式
                    first_spilit.llm_client.path = "/v1/chat/completions"
                
                st.success(f"✅ API配置已更新: {first_spilit.llm_client.host}{first_spilit.llm_client.path}")
        
    except Exception as e:
        st.warning(f"⚠️ API配置设置失败: {e}")


def test_api_connection(api_key: str, base_url: str, model: str) -> dict:
    """测试API连接"""
    try:
        # 创建临时的LLM客户端进行测试
        from LLMTool import LLMApiClient
        
        # 临时更新配置
        test_client = LLMApiClient()
        test_client.api_key = api_key
        
        if base_url:
            # 解析URL设置host和path
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            test_client.host = parsed.netloc
            
            # 根据不同的API服务设置正确的路径
            if "anthropic" in base_url.lower():
                test_client.path = "/v1/messages"
            elif "openai" in base_url.lower() or "rcouyi" in base_url.lower():
                test_client.path = "/v1/chat/completions"
            else:
                # 默认尝试OpenAI兼容格式
                test_client.path = "/v1/chat/completions"
        
        # 发送一个简单的测试请求
        test_messages = [
            {"role": "user", "content": "请回复'连接测试成功'"}
        ]
        
        st.info(f"🔍 调试信息: 正在测试 {test_client.host}{test_client.path}")
        
        response = test_client.call(test_messages, model)
        
        if response and "连接测试成功" in response:
            return {"success": True, "message": "API连接测试成功"}
        elif response:
            return {"success": True, "message": f"API连接成功，模型响应正常"}
        else:
            return {"success": False, "message": "API连接失败，未收到响应"}
            
    except Exception as e:
        error_msg = str(e)
        # 提供更详细的错误信息
        if "Connection" in error_msg:
            return {"success": False, "message": f"网络连接失败: 无法连接到 {base_url}"}
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return {"success": False, "message": "认证失败: API Key无效或权限不足"}
        elif "404" in error_msg:
            return {"success": False, "message": "服务未找到: 请检查API URL和路径"}
        elif "429" in error_msg:
            return {"success": False, "message": "请求过频: 请稍后重试"}
        elif "500" in error_msg:
            return {"success": False, "message": "服务器错误: API服务暂时不可用"}
        else:
            return {"success": False, "message": f"连接测试失败: {error_msg}"}


def render_progress_section(tracker: ProgressTracker):
    """渲染进度区域"""
    st.header("📊 处理进度")
    
    # 整体进度条
    progress_col1, progress_col2 = st.columns([3, 1])
    with progress_col1:
        st.progress(tracker.overall_progress / 100)
    with progress_col2:
        st.metric("整体进度", f"{tracker.overall_progress:.1f}%")
    
    # 当前步骤信息
    if tracker.current_step < len(tracker.steps):
        current = tracker.steps[tracker.current_step]
        if current["status"] == "active":
            st.info(f"🔄 当前步骤: {current['name']} - {current['message']}")
        elif current["status"] == "error":
            st.error(f"❌ 步骤失败: {current['name']} - {current['message']}")
    
    # 步骤详情 - 每个步骤可独立展开
    st.subheader("📋 详细步骤")
    
    for i, step in enumerate(tracker.steps):
        status_icon = {
            "pending": "⏳",
            "active": "🔄",
            "completed": "✅",
            "error": "❌"
        }.get(step["status"], "⏳")
        
        progress_text = ""
        if step["progress"] > 0:
            progress_text = f" ({step['progress']}%)"
        
        # 步骤标题
        step_title = f"{step['icon']} {step['name']}{progress_text}"
        if step["message"]:
            step_title += f" - {step['message']}"
        
        # 根据状态决定是否展开
        expanded = step["status"] in ["completed", "error"] and step.get("result") is not None
        
        with st.expander(f"{status_icon} {step_title}", expanded=expanded):
            if step["status"] == "completed" and step.get("result"):
                render_step_result(step["name"], step["result"])
            elif step["status"] == "error":
                st.error(f"❌ 错误: {step['message']}")
            elif step["status"] == "active":
                st.info(f"🔄 正在处理: {step['message']}")
            elif step["status"] == "pending":
                st.text("⏳ 等待处理...")
            else:
                st.text("📝 暂无详细信息")


def render_step_result(step_name: str, result_data: Any):
    """渲染步骤结果详情"""
    if not result_data:
        st.info("暂无结果数据")
        return
    
    if step_name == "输入验证":
        render_input_validation_result(result_data)
    elif step_name == "文本分块":
        render_text_chunking_result(result_data)
    elif step_name == "提取变量":
        render_variable_extraction_result(result_data)
    elif step_name == "后处理变量":
        render_variable_processing_result(result_data)
    elif step_name == "生成Mermaid图":
        render_mermaid_result(result_data)
    elif step_name == "拆分子系统":
        render_subsystem_result(result_data)
    elif step_name == "生成子提示词":
        render_subprompt_result(result_data)
    elif step_name == "代码生成":
        render_code_generation_result(result_data)
    elif step_name == "转换CNLP":
        render_cnlp_result(result_data)
    elif step_name == "整合结果":
        render_integration_result(result_data)
    else:
        st.json(result_data)


def render_input_validation_result(data: Any):
    """渲染输入验证结果"""
    if isinstance(data, dict):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("文本长度", f"{data.get('length', 0)} 字符")
        with col2:
            st.metric("字符编码", data.get('encoding', 'UTF-8'))
        
        if 'preview' in data:
            st.text_area("文本预览", data['preview'], height=100, disabled=True)
    else:
        st.text(f"验证结果: {data}")


def render_text_chunking_result(data: Any):
    """渲染文本分块结果"""
    if isinstance(data, dict):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("分块数量", data.get('chunk_count', 0))
        with col2:
            st.metric("块大小", f"{data.get('chunk_size', 0)} 字符")
        with col3:
            st.metric("总字符数", data.get('total_chars', 0))
        
        if 'chunks' in data:
            st.subheader("分块详情")
            
            # 分页显示分块，避免界面过长
            chunks = data['chunks']
            total_chunks = len(chunks)
            chunks_per_page = 5
            
            # 初始化分页变量
            start_idx = 0
            current_chunks = chunks
            
            # 分页控制
            if total_chunks > chunks_per_page:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    current_page = st.selectbox(
                        "选择分页",
                        options=list(range(1, (total_chunks - 1) // chunks_per_page + 2)),
                        index=0,
                        format_func=lambda x: f"第 {x} 页 (显示 {min(chunks_per_page, total_chunks - (x-1)*chunks_per_page)} 个分块)"
                    )
                
                # 计算当前页的分块范围
                start_idx = (current_page - 1) * chunks_per_page
                end_idx = min(start_idx + chunks_per_page, total_chunks)
                current_chunks = chunks[start_idx:end_idx]
                
                st.info(f"📄 第 {current_page} 页，显示分块 {start_idx + 1}-{end_idx}，共 {total_chunks} 个分块")
            else:
                st.info(f"📊 共分割出 {total_chunks} 个文本块，每个块最大 {data.get('chunk_size', 0)} 字符")
            
            # 显示当前页的分块
            for i, chunk in enumerate(current_chunks, start_idx + 1):
                with st.expander(f"分块 {i} ({len(chunk)} 字符)", expanded=(i <= 3)):
                    st.text(chunk)
    else:
        st.text(f"分块结果: {data}")


def render_variable_extraction_result(data: Any):
    """渲染变量提取结果"""
    if isinstance(data, dict) and 'variables' in data:
        variables = data['variables']
        st.metric("提取变量数量", len(variables))
        
        if variables:
            st.subheader("提取的变量")
            # 以表格形式显示变量
            var_data = []
            for i, var in enumerate(variables, 1):
                var_data.append({"序号": i, "变量名": var, "格式": f"{{{var}}}"})
            
            st.dataframe(var_data, use_container_width=True)
        else:
            st.warning("未提取到变量")
    elif isinstance(data, list):
        st.metric("提取变量数量", len(data))
        for i, var in enumerate(data, 1):
            st.text(f"{i}. {{{var}}}")
    else:
        st.text(f"变量提取结果: {data}")


def render_variable_processing_result(data: Any):
    """渲染变量后处理结果"""
    if isinstance(data, dict):
        if 'processed_text' in data:
            st.subheader("处理后的文本")
            st.text_area("处理后的文本内容", data['processed_text'], height=200, disabled=True)
        
        if 'changes' in data:
            st.subheader("处理变更")
            for change in data['changes']:
                st.text(f"• {change}")
    else:
        st.text(f"后处理结果: {data}")


def render_mermaid_result(data: Any):
    """渲染Mermaid图结果"""
    if isinstance(data, str):
        st.subheader("生成的Mermaid代码")
        st.code(data, language="mermaid")
        st.info("💡 提示: 您可以将此代码复制到Mermaid编辑器中查看图形")
    elif isinstance(data, dict) and 'mermaid_code' in data:
        st.subheader("生成的Mermaid代码")
        st.code(data['mermaid_code'], language="mermaid")
        if 'nodes_count' in data:
            st.metric("节点数量", data['nodes_count'])
    else:
        st.text(f"Mermaid生成结果: {data}")


def render_subsystem_result(data: Any):
    """渲染子系统拆分结果"""
    if isinstance(data, dict) and 'subsystems' in data:
        subsystems = data['subsystems']
        st.metric("子系统数量", len(subsystems))
        
        for i, subsystem in enumerate(subsystems, 1):
            with st.expander(f"子系统 {i}: {subsystem.get('name', '未知系统')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.text("**职责:**")
                    st.text(subsystem.get('responsibility', '无描述'))
                with col2:
                    st.text("**独立性:**")
                    st.text(subsystem.get('independence', '无描述'))
                
                st.text("**协作关系:**")
                st.text(subsystem.get('collaboration', '无描述'))
                
                modules = subsystem.get('contained_modules', [])
                if modules:
                    st.text("**包含模块:**")
                    st.text(", ".join(modules))
    else:
        st.text(f"子系统拆分结果: {data}")


def render_subprompt_result(data: Any):
    """渲染子提示词结果"""
    if isinstance(data, dict) and 'subprompts' in data:
        subprompts = data['subprompts']
        st.metric("子提示词数量", len(subprompts))
        
        for i, prompt in enumerate(subprompts, 1):
            with st.expander(f"子提示词 {i}: {prompt.get('name', f'提示词{i}')}"):
                if 'prompt' in prompt:
                    st.text_area("提示词内容", prompt['prompt'], height=150, disabled=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if 'input' in prompt:
                        st.text("**输入:**")
                        st.text(prompt['input'])
                with col2:
                    if 'output' in prompt:
                        st.text("**输出:**")
                        st.text(prompt['output'])
    else:
        st.text(f"子提示词生成结果: {data}")


def render_code_generation_result(data: Any):
    """渲染代码生成结果"""
    if isinstance(data, dict) and 'results' in data:
        results = data['results']
        summary = data.get('summary', {})
        
        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总子系统数", summary.get('total_subprompts', 0))
        with col2:
            st.metric("可实现数", summary.get('implementable_count', 0))
        with col3:
            st.metric("生成成功", summary.get('successful_count', 0))
        with col4:
            st.metric("生成失败", summary.get('failed_count', 0))
        
        # 显示每个子系统的代码生成结果
        for i, result in enumerate(results, 1):
            name = result.get('name', f'子系统{i}')
            is_implementable = result.get('is_implementable', False)
            has_code = result.get('code') is not None
            
            # 根据状态选择图标和标题颜色
            if has_code:
                icon = "✅"
                status_color = "green"
            elif is_implementable:
                icon = "⚠️"
                status_color = "orange"
            else:
                icon = "❌"
                status_color = "red"
            
            with st.expander(f"{icon} 子系统 {i}: {name}", expanded=False):
                if not is_implementable:
                    st.error(f"**不适合代码实现:** {result.get('reason', '未知原因')}")
                elif not has_code:
                    st.warning(f"**代码生成失败:** {result.get('error', '未知错误')}")
                else:
                    st.success("**代码生成成功**")
                    
                    # 显示实现注释
                    if result.get('annotation'):
                        st.info(f"**实现思路:** {result['annotation']}")
                    
                    # 显示生成的代码
                    if result.get('code'):
                        st.subheader("生成的代码")
                        st.code(result['code'], language="python")
                    
                    # 显示测试用例
                    test_cases = result.get('test_cases', [])
                    if test_cases:
                        st.subheader(f"测试用例 ({len(test_cases)} 个)")
                        for j, test_case in enumerate(test_cases, 1):
                            with st.container():
                                st.write(f"**测试用例 {j}:**")
                                col_input, col_output = st.columns(2)
                                with col_input:
                                    st.write("**输入代码:**")
                                    st.code(test_case.get('input_code', ''), language="python")
                                with col_output:
                                    st.write("**预期输出:**")
                                    st.code(test_case.get('expected_output', ''), language="text")
                
                # 显示原始提示词（折叠状态）
                with st.expander("查看原始提示词", expanded=False):
                    st.text_area("原始提示词", result.get('original_prompt', ''), height=100, disabled=True)
    else:
        st.text(f"代码生成结果: {data}")


def render_cnlp_result(data: Any):
    """渲染CNLP转换结果"""
    if isinstance(data, dict) and 'cnlp_results' in data:
        results = data['cnlp_results']
        st.metric("CNLP结构数量", len(results))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("转换成功", data.get('success_count', 0))
        with col2:
            st.metric("转换失败", data.get('failed_count', 0))
        with col3:
            st.metric("总数", data.get('total_count', 0))
        
        for i, result in enumerate(results, 1):
            with st.expander(f"CNLP {i}: {result.get('name', f'结构{i}')}"):
                if 'cnlp' in result:
                    st.code(result['cnlp'], language="yaml")
    else:
        st.text(f"CNLP转换结果: {data}")


def render_integration_result(data: Any):
    """渲染整合结果"""
    if isinstance(data, dict):
        st.success("🎉 所有步骤已完成！")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("处理步骤", len(data.get('completed_steps', [])))
        with col2:
            st.metric("总耗时", f"{data.get('total_time', 0):.1f}秒")
        with col3:
            st.metric("数据完整性", "100%" if data.get('complete', True) else "部分")
        
        if 'summary' in data:
            st.subheader("处理摘要")
            st.json(data['summary'])
    else:
        st.text(f"整合结果: {data}")


def render_logs_section(tracker: ProgressTracker, show_debug: bool):
    """渲染日志区域"""
    if show_debug and tracker.logs:
        with st.expander("🔍 详细日志", expanded=False):
            for log in tracker.logs[-20:]:  # 只显示最近20条
                st.text(log)


def render_results_section(result_data: Dict[str, Any]):
    """渲染结果区域"""
    if not result_data:
        return
    
    st.header("📋 处理结果")
    
    # 统计信息
    st.subheader("📊 统计信息")
    col1, col2, col3, col4 = st.columns(4)
    
    # 提取统计数据
    step1_data = result_data.get("step1_result", {})
    step2_data = result_data.get("step2_result", {})
    step3_data = result_data.get("step3_result", {})
    
    variables_count = len(step1_data.get("variables", []))
    subsystems_count = len(step2_data.get("subsystems", {}).get("subsystems", []))
    subprompts_count = len(step2_data.get("subprompts", {}).get("subprompts", []))
    cnlp_count = len(step3_data.get("cnlp_results", []))
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{variables_count}</div>
            <div class="stat-label">提取变量</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{subsystems_count}</div>
            <div class="stat-label">子系统</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{subprompts_count}</div>
            <div class="stat-label">子提示词</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{cnlp_count}</div>
            <div class="stat-label">CNLP结果</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 结果选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["🔤 提取变量", "🧩 子系统拆分", "📝 CNLP结果", "🔗 协作关系"])
    
    with tab1:
        render_variables_tab(step1_data)
    
    with tab2:
        render_subsystems_tab(step2_data)
    
    with tab3:
        render_cnlp_tab(step3_data)
    
    with tab4:
        render_collaboration_tab(step2_data)


def render_variables_tab(step1_data: Dict[str, Any]):
    """渲染变量提取结果"""
    variables = step1_data.get("variables", [])
    
    if variables:
        st.success(f"✅ 成功提取 {len(variables)} 个变量")
        
        # 变量列表
        for i, var in enumerate(variables, 1):
            st.markdown(f"**{i}.** `{{{var}}}`")
        
        # 处理后的文本
        if "text_with_vars" in step1_data:
            st.subheader("📄 变量标记后的文本")
            with st.expander("查看完整文本"):
                st.text(step1_data["text_with_vars"])
    else:
        st.warning("⚠️ 未提取到变量")


def render_subsystems_tab(step2_data: Dict[str, Any]):
    """渲染子系统拆分结果"""
    subsystems_data = step2_data.get("subsystems", {})
    subsystems = subsystems_data.get("subsystems", [])
    
    if subsystems:
        st.success(f"✅ 成功拆分 {len(subsystems)} 个子系统")
        
        for i, subsystem in enumerate(subsystems, 1):
            with st.expander(f"🔧 子系统 {i}: {subsystem.get('name', '未知系统')}"):
                st.markdown(f"**职责**: {subsystem.get('responsibility', '无描述')}")
                st.markdown(f"**独立性**: {subsystem.get('independence', '无描述')}")
                st.markdown(f"**协作关系**: {subsystem.get('collaboration', '无描述')}")
                
                modules = subsystem.get('contained_modules', [])
                if modules:
                    st.markdown(f"**包含模块**: {', '.join(modules)}")
    
    # Mermaid图
    mermaid_content = step2_data.get("mermaid_content", "")
    if mermaid_content:
        st.subheader("🎨 系统流程图")
        with st.expander("查看Mermaid代码"):
            st.code(mermaid_content, language="mermaid")


def render_cnlp_tab(step3_data: Dict[str, Any]):
    """渲染CNLP结果"""
    cnlp_results = step3_data.get("cnlp_results", [])
    
    if cnlp_results:
        st.success(f"✅ 成功生成 {len(cnlp_results)} 个CNLP结构")
        
        for i, cnlp in enumerate(cnlp_results, 1):
            with st.expander(f"📋 CNLP {i}: {cnlp.get('title', f'结构{i}')}"):
                st.json(cnlp)
    else:
        st.warning("⚠️ 未生成CNLP结果")


def render_collaboration_tab(step2_data: Dict[str, Any]):
    """渲染协作关系"""
    subsystems_data = step2_data.get("subsystems", {})
    subsystems = subsystems_data.get("subsystems", [])
    
    if subsystems:
        st.success("🔗 系统协作关系图")
        
        # 文本形式的协作关系
        collaboration_text = ""
        for i, subsystem in enumerate(subsystems, 1):
            name = subsystem.get('name', f'系统{i}')
            collaboration = subsystem.get('collaboration', '无协作信息')
            collaboration_text += f"**{name}**:\n{collaboration}\n\n"
        
        st.markdown(collaboration_text)
        
        st.info("💡 后续版本将支持交互式Mermaid流程图渲染")
    else:
        st.warning("⚠️ 无协作关系数据")


def process_text_async(input_text: str, chunk_size: int, max_workers: int, tracker: ProgressTracker):
    """异步处理文本，使用优化的进度回调系统"""
    try:
        # 导入处理模块
        from run_split import PromptSplitPipeline
        from common_utils import LogUtils, ConfigUtils
        
        # 定义步骤到索引的映射
        step_mapping = {
            "输入验证": 0,
            "文本分块": 1,
            "提取变量": 2,
            "后处理变量": 3,
            "生成Mermaid图": 4,
            "拆分子系统": 5,
            "生成子提示词": 6,
            "代码生成": 7,
            "转换CNLP": 8,
            "整合结果": 9
        }
        
        # 创建进度回调函数
        def progress_callback(step_name: str, progress: int, message: str = "", result_data: Any = None):
            """进度回调函数，将pipeline进度映射到UI进度"""
            if step_name in step_mapping:
                step_idx = step_mapping[step_name]
                if progress == 0:
                    tracker.start_step(step_idx, message)
                elif progress == 100:
                    tracker.complete_step(step_idx, message, result_data)
                else:
                    tracker.update_step_progress(step_idx, progress, message, result_data)
        
        # 创建带进度回调的处理管道
        pipeline = PromptSplitPipeline(progress_callback=progress_callback)
        
        # 使用用户配置的API Key
        if st.session_state.get('api_key'):
            setup_user_api_config(st.session_state.api_key, 
                                 st.session_state.get('api_base_url', ''), 
                                 st.session_state.get('api_model', ''))
        
        # 输入验证步骤（单独处理，因为这是UI层面的验证）
        tracker.start_step(step_mapping["输入验证"], "验证输入文本...")
        validation_result = {
            "length": len(input_text),
            "encoding": "UTF-8",
            "preview": input_text[:200] + "..." if len(input_text) > 200 else input_text
        }
        tracker.complete_step(step_mapping["输入验证"], f"文本长度: {len(input_text)} 字符", validation_result)
        
        # 步骤1: 变量提取（现在会通过进度回调自动更新结果）
        step1_result = pipeline.step1_extract_variables(input_text)
        if "error" in step1_result:
            tracker.error_step(step_mapping.get("提取变量", 2), step1_result["error"])
            return
        
        # 步骤2: 子系统拆分（现在会通过进度回调自动更新结果）
        step2_result = pipeline.step2_split_to_subprompts(step1_result["text_with_vars"])
        if "error" in step2_result:
            tracker.error_step(step_mapping.get("拆分子系统", 5), step2_result["error"])
            return
        
        # 步骤2.5: 代码生成（新增步骤，可配置禁用）
        config = ConfigUtils.get_config()
        code_generation_enabled = config.get('step2_5_code_generation', {}).get('enabled', True)
        
        if code_generation_enabled:
            step2_5_result = pipeline.step2_5_generate_code(step2_result.get("subprompts", {}))
            if "error" in step2_5_result:
                # 代码生成失败不中断整个流程，只记录警告
                LogUtils.log_warning(f"代码生成失败，但继续执行后续步骤: {step2_5_result['error']}")
                step2_5_result = {"error": step2_5_result["error"], "results": []}
        else:
            LogUtils.log_info("代码生成步骤已禁用，跳过...")
            step2_5_result = {
                "summary": {"total_count": 0, "implementable_count": 0, "successful_count": 0, "failed_count": 0},
                "results": [],
                "disabled": True
            }
        
        # 步骤3: CNLP转换（跳过已生成代码的子系统）
        step3_result = pipeline.step3_convert_to_cnlp(step2_result.get("subprompts", {}), step2_5_result)
        if "error" in step3_result:
            tracker.error_step(step_mapping.get("转换CNLP", 8), step3_result["error"])
            return
        
        # 最终整合
        tracker.start_step(step_mapping["整合结果"], "整合最终结果...")
        
        # 计算统计信息
        end_time = time.time()
        # 使用真实的处理时间
        if tracker.start_time:
            processing_time = end_time - tracker.start_time
        else:
            processing_time = 0.0  # 后备方案
        
        integration_summary = {
            "completed_steps": [step["name"] for step in tracker.steps if step["status"] == "completed"],
            "total_time": round(processing_time, 2),
            "complete": True,
            "summary": {
                "variables_extracted": len(step1_result.get("variables", [])),
                "subsystems_created": len(step2_result.get("subsystems", {}).get("subsystems", [])),
                "subprompts_generated": len(step2_result.get("subprompts", {}).get("subprompts", [])),
                "code_implementable": step2_5_result.get("summary", {}).get("implementable_count", 0),
                "code_successful": step2_5_result.get("summary", {}).get("successful_count", 0),
                "cnlp_converted": len(step3_result.get("cnlp_results", [])),
                "cnlp_skipped": step3_result.get("skipped_count", 0)
            }
        }
        
        final_result = {
            "step1_result": step1_result,
            "step2_result": step2_result,
            "step2_5_result": step2_5_result,
            "step3_result": step3_result,
            "processing_time": time.time()
        }
        
        tracker.complete_step(step_mapping["整合结果"], "处理完成", integration_summary)
        
        # 设置结果和完成状态
        tracker.result = final_result
        tracker.processing_complete = True
        
        # 注意：不在后台线程中直接操作st.session_state，避免ScriptRunContext警告
        # 会话状态更新将在主线程中处理
        
    except Exception as e:
        tracker.error_step(tracker.current_step, f"处理异常: {str(e)}")
        tracker.processing_complete = True
        tracker.has_error = True


def main():
    """主函数"""
    initialize_session_state()
    
    # 渲染页面
    render_header()
    
    # 输入区域
    input_text, chunk_size, max_workers, show_debug = render_input_section()
    
    # 开始处理按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # 检查API配置状态
        api_configured = bool(st.session_state.get('api_key'))
        
        if st.button("🚀 开始处理", type="primary", use_container_width=True, disabled=not api_configured):
            if not api_configured:
                st.error("❌ 请先配置API Key")
            elif input_text.strip():
                st.session_state.processing = True
                st.session_state.progress_tracker.reset()
                st.session_state.result_data = None
                
                # 启动异步处理
                threading.Thread(
                    target=process_text_async,
                    args=(input_text, chunk_size, max_workers, st.session_state.progress_tracker)
                ).start()
                
                st.rerun()
            else:
                st.error("❌ 请输入需要处理的文本内容")
        
        # 提示信息
        if not api_configured:
            st.info("💡 请先在上方配置您的API Key才能开始处理")
    
    # 进度区域
    if st.session_state.processing or st.session_state.progress_tracker.overall_progress > 0:
        render_progress_section(st.session_state.progress_tracker)
        render_logs_section(st.session_state.progress_tracker, show_debug)
        
        # 检查后台处理是否完成（避免在后台线程中直接操作session_state）
        if st.session_state.processing:
            tracker = st.session_state.progress_tracker
            if tracker.processing_complete:
                # 处理完成，更新session_state
                st.session_state.processing = False
                if tracker.result and not tracker.has_error:
                    st.session_state.result_data = tracker.result
                    st.success("🎉 处理完成！")
                elif tracker.has_error:
                    st.error("❌ 处理过程中发生错误，请查看详细日志")
            else:
                # 继续处理中，自动刷新
                time.sleep(1)
                st.rerun()
    
    # 结果区域
    if st.session_state.result_data:
        render_results_section(st.session_state.result_data)
        
        # 下载结果按钮
        st.subheader("💾 导出结果")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            result_json = json.dumps(st.session_state.result_data, ensure_ascii=False, indent=2)
            st.download_button(
                "📄 下载JSON结果",
                result_json,
                "prompt_split_result.json",
                "application/json"
            )
        
        with col2:
            # 生成处理报告
            variables = st.session_state.result_data["step1_result"].get("variables", [])
            code_summary = st.session_state.result_data.get("step2_5_result", {}).get("summary", {})
            report = f"""# AI提示词拆分处理报告

## 处理统计
- 提取变量数量: {len(variables)}
- 子系统数量: {len(st.session_state.result_data["step2_result"].get("subsystems", {}).get("subsystems", []))}
- 可实现代码数量: {code_summary.get("implementable_count", 0)}
- 成功生成代码数量: {code_summary.get("successful_count", 0)}
- 生成CNLP数量: {len(st.session_state.result_data["step3_result"].get("cnlp_results", []))}

## 提取的变量
{chr(10).join([f"- {{{var}}}" for var in variables])}

## 处理时间
{time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            st.download_button(
                "📊 下载处理报告",
                report,
                "prompt_split_report.md",
                "text/markdown"
            )


if __name__ == "__main__":
    main() 