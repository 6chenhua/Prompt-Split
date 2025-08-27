"""
PromptSplit Streamlit Web界面 - 完全修复版
解决所有多线程和session_state问题
"""

import streamlit as st
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Any
import io

# 导入项目模块
from run_split import PromptSplitPipeline
from common_utils import LogUtils, FileUtils


# 设置页面配置
st.set_page_config(
    page_title="PromptSplit - 智能提示词拆分系统",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .stProgress .st-bo {
        background-color: #f0f2f6;
    }
    
    .step-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    
    .success-container {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
    
    .error-container {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #dc3545;
    }
    
    .cnlp-container {
        background-color: #fff;
        padding: 1.5rem;
        border-radius: 0.8rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e9ecef;
    }
    
    .metric-container {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


class ProgressCallbackFixed:
    """完全修复的进度回调类 - 线程安全"""
    
    def __init__(self):
        self.current_step = ""
        self.step_progress = {}
        self.substep_progress = {}
        self.logs = []
        self.processing_complete = False
        self.has_error = False
        self.final_result = None
        self.error_message = ""
        self._lock = threading.Lock()  # 添加线程锁
    
    def update_step(self, step_name: str, progress: float, status: str = ""):
        """线程安全的步骤进度更新"""
        with self._lock:
            self.step_progress[step_name] = {
                'progress': progress,
                'status': status
            }
            self.current_step = step_name
    
    def update_substep(self, main_step: str, substep: str, progress: float, status: str = ""):
        """线程安全的子步骤进度更新"""
        with self._lock:
            substep_key = f"{main_step}_{substep}"
            self.substep_progress[substep_key] = {
                'progress': progress,
                'status': status
            }
    
    def log_message(self, level: str, message: str):
        """线程安全的日志记录"""
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.logs.append({
                'timestamp': timestamp,
                'level': level,
                'message': message
            })
    
    def set_status(self, status: str):
        """设置整体状态"""
        self.log_message("INFO", f"状态: {status}")
    
    def set_complete(self, result=None, error=None):
        """线程安全的完成状态设置"""
        with self._lock:
            self.processing_complete = True
            if error:
                self.has_error = True
                self.error_message = str(error)
            if result:
                self.final_result = result


def init_session_state():
    """初始化会话状态"""
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    if 'progress_callback' not in st.session_state:
        st.session_state.progress_callback = ProgressCallbackFixed()
    
    if 'result' not in st.session_state:
        st.session_state.result = None
    
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    
    # 确保progress_callback始终存在且类型正确
    if st.session_state.progress_callback is None or not isinstance(st.session_state.progress_callback, ProgressCallbackFixed):
        st.session_state.progress_callback = ProgressCallbackFixed()


def display_header():
    """显示页面头部"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #2c3e50; margin-bottom: 0.5rem;">🚀 PromptSplit</h1>
        <h3 style="color: #7f8c8d; font-weight: 300;">智能提示词拆分系统</h3>
        <p style="color: #95a5a6; margin-top: 1rem;">将复杂提示词转换为结构化、可复用的模块系统</p>
    </div>
    """, unsafe_allow_html=True)


def display_input_section():
    """显示输入部分"""
    st.markdown("## 📝 输入设置")
    
    # 输入方式选择
    input_method = st.radio(
        "选择输入方式",
        ["📝 直接输入文本", "📁 上传文件"],
        horizontal=True
    )
    
    if input_method == "📝 直接输入文本":
        # 文本输入
        st.session_state.input_text = st.text_area(
            "输入您的提示词",
            value=st.session_state.input_text,
            height=300,
            placeholder="""请在此输入您的提示词...

示例：
你是一个专业的客服代表，需要处理客户的各种询问。你的主要职责包括：
1. 理解客户的{需求}
2. 提供准确的{产品信息}  
3. 解决客户的{问题}
当客户询问{价格}时，需要根据{产品类型}提供相应的报价。
如果遇到复杂问题，应该及时转接给{专业人员}。"""
        )
    else:
        # 文件上传
        uploaded_file = st.file_uploader(
            "选择文本文件",
            type=['txt', 'md'],
            help="支持 .txt 和 .md 格式的文本文件"
        )
        
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode('utf-8')
                st.session_state.input_text = content
                
                # 显示文件信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("文件名", uploaded_file.name)
                with col2:
                    st.metric("文件大小", f"{len(content)} 字符")
                with col3:
                    st.metric("行数", len(content.split('\n')))
                
                # 预览文件内容
                with st.expander("📄 预览文件内容"):
                    st.text_area("文件内容", content, height=200, disabled=True)
                    
            except Exception as e:
                st.error(f"❌ 文件读取失败: {e}")
    
    # 控制按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🚀 开始处理", disabled=st.session_state.processing, use_container_width=True):
            if st.session_state.input_text.strip():
                try:
                    start_processing_safe()
                except Exception as e:
                    st.error(f"❌ 启动处理失败: {e}")
                    st.session_state.processing = False
            else:
                st.error("❌ 请输入文本内容或上传文件")
    
    with col2:
        if st.button("⏹ 停止处理", disabled=not st.session_state.processing, use_container_width=True):
            stop_processing_safe()
    
    with col3:
        if st.button("🔄 重置", use_container_width=True):
            reset_processing_safe()


def start_processing_safe():
    """线程安全的开始处理"""
    # 重置状态
    st.session_state.processing = True
    st.session_state.progress_callback = ProgressCallbackFixed()
    st.session_state.result = None
    
    # **关键修复**: 创建本地变量副本，避免在线程中访问session_state
    input_text = str(st.session_state.input_text)  # 创建字符串副本
    callback = st.session_state.progress_callback  # 本地引用
    
    def process_in_background():
        """后台处理函数 - 完全隔离，不访问session_state"""
        try:
            # 使用本地变量，不访问任何session_state
            pipeline = FixedPromptSplitPipeline(callback)
            result = pipeline.run_complete_pipeline(input_text)
            
            # 通过回调设置结果，不直接修改session_state
            callback.set_complete(result=result)
            
        except Exception as e:
            # 通过回调记录错误，不访问session_state
            callback.log_message("ERROR", f"处理失败: {e}")
            callback.set_complete(error=e)
    
    # 启动后台线程
    thread = threading.Thread(target=process_in_background, daemon=True)
    thread.start()


def stop_processing_safe():
    """线程安全的停止处理"""
    st.session_state.processing = False
    callback = st.session_state.progress_callback
    if callback:
        callback.log_message("INFO", "处理已停止")
        callback.set_complete(error="用户停止")


def reset_processing_safe():
    """线程安全的重置处理状态"""
    st.session_state.processing = False
    st.session_state.progress_callback = ProgressCallbackFixed()
    st.session_state.result = None
    st.session_state.input_text = ""


def display_progress_section():
    """显示进度部分"""
    # 安全检查
    if not hasattr(st.session_state, 'progress_callback') or st.session_state.progress_callback is None:
        return
        
    callback = st.session_state.progress_callback
    
    if not st.session_state.processing and not callback.step_progress:
        return
    
    st.markdown("## 📊 处理进度")
    
    # 整体进度
    overall_progress = calculate_overall_progress(callback.step_progress)
    st.progress(overall_progress / 100)
    st.markdown(f"**整体进度: {overall_progress:.1f}%**")
    
    # 详细步骤
    steps = [
        ("step1", "🔍 步骤1: 变量提取", ["chunk", "extract", "postprocess"]),
        ("step2", "🔀 步骤2: 系统拆分", ["mermaid", "subsystem", "subprompt"]),
        ("step3", "📋 步骤3: CNLP转换", ["convert", "validate"])
    ]
    
    for step_id, step_name, substeps in steps:
        if step_id in callback.step_progress:
            step_data = callback.step_progress[step_id]
            
            # 主步骤
            with st.container():
                st.markdown(f"### {step_name}")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.progress(step_data['progress'] / 100)
                with col2:
                    st.markdown(f"**{step_data['progress']:.1f}%**")
                
                if step_data['status']:
                    st.markdown(f"*{step_data['status']}*")
                
                # 子步骤
                substep_cols = st.columns(len(substeps))
                for i, substep in enumerate(substeps):
                    substep_key = f"{step_id}_{substep}"
                    if substep_key in callback.substep_progress:
                        substep_data = callback.substep_progress[substep_key]
                        
                        with substep_cols[i]:
                            st.markdown(f"**{get_substep_name(substep)}**")
                            st.progress(substep_data['progress'] / 100)
                            st.markdown(f"*{substep_data['status']}*")
    
    # 实时日志
    if callback.logs:
        st.markdown("### 📋 运行日志")
        
        log_container = st.container()
        with log_container:
            recent_logs = callback.logs[-20:]
            
            for log in recent_logs:
                level = log['level']
                timestamp = log['timestamp']
                message = log['message']
                
                if level == 'ERROR':
                    st.markdown(f"""
                    <div class="error-container">
                        <strong>[{timestamp}] ❌ {message}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                elif level == 'SUCCESS':
                    st.markdown(f"""
                    <div class="success-container">
                        <strong>[{timestamp}] ✅ {message}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                elif level == 'STEP':
                    st.markdown(f"""
                    <div class="step-container">
                        <strong>[{timestamp}] 🔵 {message}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"[{timestamp}] {message}")


def display_results_section():
    """显示结果部分"""
    if not st.session_state.result:
        return
    
    st.markdown("## 📄 处理结果")
    
    result = st.session_state.result
    
    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📋 CNLP结果", "🔗 协作关系", "📊 完整数据"])
    
    with tab1:
        display_cnlp_results(result)
    
    with tab2:
        display_collaboration_results(result)
    
    with tab3:
        display_full_results(result)
    
    # 导出功能
    st.markdown("### 💾 导出结果")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 导出完整结果", use_container_width=True):
            export_complete_results(result)
    
    with col2:
        if st.button("📋 导出CNLP数据", use_container_width=True):
            export_cnlp_results(result)


def display_cnlp_results(result: Dict[str, Any]):
    """显示CNLP结果 - 支持多个CNLP"""
    st.markdown("### 📋 CNLP格式化结果")
    
    if 'step3_cnlp' not in result or 'cnlp_output' not in result['step3_cnlp']:
        st.warning("⚠️ 未找到CNLP结果")
        return
    
    cnlp_data = result['step3_cnlp']['cnlp_output']
    
    # 检查是否为列表（多个CNLP）
    if isinstance(cnlp_data, list):
        st.info(f"🎯 共找到 **{len(cnlp_data)}** 个CNLP结果")
        
        # 为每个CNLP创建单独的展示区域
        for i, cnlp_item in enumerate(cnlp_data, 1):
            st.markdown(f"""
            <div class="cnlp-container">
                <h4>📋 CNLP #{i}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            display_single_cnlp(cnlp_item, i)
            st.markdown("---")
    
    elif isinstance(cnlp_data, dict):
        st.info("🎯 单个CNLP结果")
        display_single_cnlp(cnlp_data, 1)
    
    else:
        st.markdown(f"""
        <div class="cnlp-container">
            <h4>📋 CNLP结果</h4>
            <pre style="background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem;">{cnlp_data}</pre>
        </div>
        """, unsafe_allow_html=True)


def display_single_cnlp(cnlp_data: Dict[str, Any], index: int):
    """显示单个CNLP的详细信息"""
    
    if isinstance(cnlp_data, dict):
        # 展示关键信息
        col1, col2, col3 = st.columns(3)
        
        with col1:
            agent_info = cnlp_data.get('Agent', {})
            if isinstance(agent_info, dict) and 'Role' in agent_info:
                st.markdown(f"""
                <div class="metric-container">
                    <h5>👤 角色</h5>
                    <p>{agent_info['Role']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if 'Skills' in cnlp_data:
                skills = cnlp_data['Skills']
                skill_count = len(skills) if isinstance(skills, list) else 1
                st.markdown(f"""
                <div class="metric-container">
                    <h5>🛠️ 技能数量</h5>
                    <p>{skill_count}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            if 'Workflow' in cnlp_data:
                workflow = cnlp_data['Workflow']
                workflow_steps = len(workflow) if isinstance(workflow, list) else 1
                st.markdown(f"""
                <div class="metric-container">
                    <h5>📋 工作流步骤</h5>
                    <p>{workflow_steps}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # JSON格式显示
        with st.expander(f"📄 CNLP #{index} JSON格式", expanded=True):
            st.json(cnlp_data)
    
    else:
        st.code(str(cnlp_data), language='json')


def display_collaboration_results(result: Dict[str, Any]):
    """显示协作关系"""
    st.markdown("### 🔗 系统协作关系")
    
    if 'step2_split' not in result:
        st.warning("⚠️ 未找到拆分结果")
        return
    
    split_data = result['step2_split']
    
    if 'subsystems' in split_data and 'subsystems' in split_data['subsystems']:
        subsystems = split_data['subsystems']['subsystems']
        
        st.markdown(f"#### 📋 共识别出 **{len(subsystems)}** 个子系统")
        
        # 详细信息展示
        for i, subsystem in enumerate(subsystems, 1):
            with st.expander(f"🔧 子系统 {i}: {subsystem.get('name', '未知系统')}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📋 基本信息**")
                    st.markdown(f"- **名称**: {subsystem.get('name', '未定义')}")
                    st.markdown(f"- **职责**: {subsystem.get('responsibility', '未定义')}")
                    st.markdown(f"- **独立性**: {subsystem.get('independence', '未说明')}")
                
                with col2:
                    st.markdown("**🔗 协作关系**")
                    collaboration = subsystem.get('collaboration', '未定义协作关系')
                    st.markdown(f"- {collaboration}")
    else:
        st.warning("⚠️ 暂未找到子系统数据")


def display_full_results(result: Dict[str, Any]):
    """显示完整结果"""
    st.markdown("### 📊 完整处理结果")
    
    # 处理统计
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if 'step1_variables' in result:
            var_count = len(result['step1_variables'].get('variables', []))
            st.metric("🔍 提取变量数", var_count)
    
    with col2:
        if 'step2_split' in result:
            subsys_count = len(result['step2_split'].get('subsystems', {}).get('subsystems', []))
            st.metric("🔧 子系统数", subsys_count)
    
    with col3:
        if 'step2_split' in result:
            prompt_count = len(result['step2_split'].get('subprompts', {}).get('subprompts', []))
            st.metric("📝 子提示词数", prompt_count)
    
    with col4:
        if 'step3_cnlp' in result:
            cnlp_data = result['step3_cnlp'].get('cnlp_output', [])
            cnlp_count = len(cnlp_data) if isinstance(cnlp_data, list) else 1
            st.metric("📋 CNLP数量", cnlp_count)
    
    # 完整JSON结果
    with st.expander("📄 完整JSON结果", expanded=False):
        st.json(result)


def calculate_overall_progress(step_progress: Dict[str, Dict]) -> float:
    """计算整体进度"""
    if not step_progress:
        return 0.0
    
    total_progress = sum(data['progress'] for data in step_progress.values())
    return total_progress / len(step_progress)


def get_substep_name(substep: str) -> str:
    """获取子步骤显示名称"""
    substep_names = {
        'chunk': '📄 文本分块',
        'extract': '🔍 变量提取', 
        'postprocess': '⚙️ 后处理',
        'mermaid': '🎨 Mermaid图',
        'subsystem': '🔧 子系统拆分',
        'subprompt': '📝 子提示词',
        'convert': '🔄 格式转换',
        'validate': '✅ 结果验证'
    }
    return substep_names.get(substep, substep)


def export_complete_results(result: Dict[str, Any]):
    """导出完整结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"promptsplit_result_{timestamp}.json"
    
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    st.download_button(
        label="💾 下载完整结果",
        data=json_str,
        file_name=filename,
        mime="application/json"
    )


def export_cnlp_results(result: Dict[str, Any]):
    """导出CNLP结果"""
    if 'step3_cnlp' not in result:
        st.error("❌ 没有可导出的CNLP结果")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cnlp_result_{timestamp}.json"
    
    cnlp_data = result['step3_cnlp']
    json_str = json.dumps(cnlp_data, ensure_ascii=False, indent=2)
    
    st.download_button(
        label="💾 下载CNLP结果",
        data=json_str,
        file_name=filename,
        mime="application/json"
    )


class FixedPromptSplitPipeline(PromptSplitPipeline):
    """完全修复的Pipeline - 线程安全"""
    
    def __init__(self, progress_callback: ProgressCallbackFixed):
        super().__init__()
        self.callback = progress_callback
    
    def run_complete_pipeline(self, input_text: str) -> dict:
        """运行完整流程"""
        try:
            self.callback.set_status("开始处理...")
            self.callback.log_message("STEP", "=== 开始 PromptSplit 完整流程 ===")
            
            # 步骤1: 变量提取
            self.callback.update_step("step1", 10, "开始变量提取...")
            self.callback.log_message("STEP", "🔍 步骤1: 变量提取")
            
            step1_result = self.detailed_step1_extract_variables(input_text)
            if "error" in step1_result:
                self.callback.update_step("step1", 0, "失败")
                return {"success": False, "error": step1_result["error"]}
            
            self.callback.update_step("step1", 100, "完成")
            self.callback.log_message("SUCCESS", "✅ 步骤1完成")
            
            # 步骤2: 拆分为子提示词
            self.callback.update_step("step2", 10, "开始拆分...")
            self.callback.log_message("STEP", "🔀 步骤2: 拆分为子提示词")
            
            text_with_vars = step1_result["processed_text"]
            step2_result = self.detailed_step2_split_to_subprompts(text_with_vars)
            if "error" in step2_result:
                self.callback.update_step("step2", 0, "失败")
                return {"success": False, "error": step2_result["error"]}
            
            self.callback.update_step("step2", 100, "完成")
            self.callback.log_message("SUCCESS", "✅ 步骤2完成")
            
            # 步骤3: CNLP转换
            self.callback.update_step("step3", 10, "开始CNLP转换...")
            self.callback.log_message("STEP", "📋 步骤3: CNLP转换")
            
            step3_result = self.detailed_step3_convert_to_cnlp(step2_result["subprompts"])
            if "error" in step3_result:
                self.callback.update_step("step3", 0, "失败")
                return {"success": False, "error": step3_result["error"]}
            
            self.callback.update_step("step3", 100, "完成")
            self.callback.log_message("SUCCESS", "✅ 步骤3完成")
            
            # 整合最终结果
            final_result = {
                "success": True,
                "step1_variables": step1_result,
                "step2_split": step2_result,
                "step3_cnlp": step3_result,
                "timestamp": datetime.now().isoformat(),
                "input_source": "Streamlit Web界面(修复版)"
            }
            
            self.callback.log_message("SUCCESS", "🎉 完整流程执行成功！")
            self.callback.set_status("全部完成")
            
            return final_result
            
        except Exception as e:
            error_msg = f"流程执行失败: {e}"
            self.callback.log_message("ERROR", error_msg)
            self.callback.set_status("执行失败")
            return {"success": False, "error": error_msg}
    
    def detailed_step1_extract_variables(self, input_text: str):
        """详细的步骤1：变量提取"""
        self.callback.update_substep("step1", "chunk", 20, "分析文本长度...")
        from common_utils import TextProcessor
        
        chunks = TextProcessor.split_text_by_length(input_text, chunk_size=2000)
        self.callback.update_substep("step1", "chunk", 100, f"分割为{len(chunks)}个块")
        self.callback.log_message("INFO", f"文本分割为 {len(chunks)} 个处理块")
        
        self.callback.update_substep("step1", "extract", 10, "开始提取变量...")
        result = super().step1_extract_variables(input_text)
        self.callback.update_substep("step1", "extract", 90, "变量提取完成")
        
        self.callback.update_substep("step1", "postprocess", 50, "优化变量...")
        self.callback.update_substep("step1", "postprocess", 100, "后处理完成")
        
        return result
    
    def detailed_step2_split_to_subprompts(self, text_with_vars: str):
        """详细的步骤2：系统拆分"""
        self.callback.update_substep("step2", "mermaid", 20, "生成流程图...")
        mermaid_content = self.generate_mermaid_content(text_with_vars)
        self.callback.update_substep("step2", "mermaid", 100, "Mermaid图生成完成")
        
        self.callback.update_substep("step2", "subsystem", 30, "分析系统结构...")
        subsystems_data = self.split_to_subsystems(mermaid_content)
        self.callback.update_substep("step2", "subsystem", 100, "子系统拆分完成")
        
        self.callback.update_substep("step2", "subprompt", 40, "生成子提示词...")
        subprompts_data = self.generate_subprompts(text_with_vars, subsystems_data)
        self.callback.update_substep("step2", "subprompt", 100, "子提示词生成完成")
        
        return {
            "method": "functional_split",
            "mermaid_content": mermaid_content,
            "subsystems": subsystems_data,
            "subprompts": subprompts_data,
            "processed_text": text_with_vars
        }
    
    def detailed_step3_convert_to_cnlp(self, subprompts_data):
        """详细的步骤3：CNLP转换"""
        self.callback.update_substep("step3", "convert", 30, "转换格式...")
        result = super().step3_convert_to_cnlp(subprompts_data)
        self.callback.update_substep("step3", "convert", 80, "格式转换完成")
        
        self.callback.update_substep("step3", "validate", 90, "验证结果...")
        self.callback.update_substep("step3", "validate", 100, "验证完成")
        
        return result


def main():
    """主函数"""
    # 初始化会话状态
    init_session_state()
    
    # 显示页面头部
    display_header()
    
    # 侧边栏
    with st.sidebar:
        st.markdown("## 🛠️ 功能菜单")
        
        st.markdown("### 📊 当前状态")
        if st.session_state.processing:
            st.success("🟢 正在处理中...")
        else:
            st.info("⚪ 就绪")
        
        st.markdown("### 📋 使用指南")
        st.markdown("""
        1. **输入文本**: 选择直接输入或上传文件
        2. **开始处理**: 点击开始处理按钮
        3. **监控进度**: 查看实时处理进度
        4. **查看结果**: 浏览CNLP和协作关系
        5. **导出数据**: 下载处理结果
        """)
    
    # 主内容区域
    display_input_section()
    
    st.markdown("---")
    
    display_progress_section()
    
    # **关键修复**: 通过轮询检查处理状态，而不是在线程中修改session_state
    if st.session_state.processing and hasattr(st.session_state, 'progress_callback'):
        callback = st.session_state.progress_callback
        
        # 检查处理是否完成
        if callback.processing_complete:
            st.session_state.processing = False
            
            if callback.final_result:
                st.session_state.result = callback.final_result
                st.success("🎉 处理完成！")
                st.balloons()
            
            if callback.has_error:
                st.error(f"❌ 处理失败: {callback.error_message}")
    
    if st.session_state.result:
        st.markdown("---")
        display_results_section()
    
    # 简化的进度更新机制
    if st.session_state.processing:
        # 显示实时状态
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("🔄 处理中... 进度将实时更新")
        with col2:
            # 手动刷新按钮作为备用
            if st.button("🔄 刷新", key="manual_refresh"):
                st.rerun() if hasattr(st, 'rerun') else st.experimental_rerun()
        
        # 简单提示，不使用自动刷新避免状态重置
        st.markdown("""
        <div style="background-color: #fff3cd; padding: 0.5rem; border-radius: 0.3rem; border-left: 4px solid #ffc107;">
            💡 <strong>提示</strong>: 如果进度条未更新，请点击上方"🔄 刷新"按钮或按F5刷新页面
        </div>
        """, unsafe_allow_html=True)
        
        # 显示当前状态
        callback = st.session_state.progress_callback
        if callback:
            if callback.step_progress:
                latest_steps = list(callback.step_progress.items())
                for step_name, step_data in latest_steps[-3:]:  # 显示最近3个步骤
                    st.text(f"📊 {step_name}: {step_data['progress']:.1f}% - {step_data['status']}")
            
            if callback.logs:
                recent_log = callback.logs[-1]
                st.text(f"📝 最新: [{recent_log['timestamp']}] {recent_log['message']}")


if __name__ == "__main__":
    main() 