"""
CCTDI批判性思维评估系统 - Web界面
支持多人并发访问的Streamlit Web应用
"""
import streamlit as st
import uuid
import json
from datetime import datetime
from cctdi_system import CCTDIAssessmentSystem

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="CCTDI 批判性思维评估",
    page_icon="☆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== 自定义CSS样式 ====================
def load_custom_css():
    """加载自定义CSS样式 - 简约专业风格"""
    st.markdown("""
    <style>
    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* 整体布局 */
    .main {
        max-width: 1000px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }

    /* 标题样式 */
    h1 {
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    h3 {
        color: #374151;
        margin-top: 2rem;
    }

    /* 卡片样式 */
    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* 进度条样式 */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #06B6D4 0%, #3B82F6 100%);
        border-radius: 10px;
    }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 2rem;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* 聊天消息样式 */
    .stChatMessage {
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    /* 输入框样式 */
    .stChatInputContainer {
        border-top: 1px solid #E5E7EB;
        padding-top: 1rem;
    }

    /* 信息框样式 */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid #06B6D4;
    }

    /* 分隔线 */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #E5E7EB;
    }
    </style>
    """, unsafe_allow_html=True)


# ==================== 会话状态初始化 ====================
def initialize_session_state():
    """初始化会话状态 - 支持多用户并发"""

    # 为每个用户生成唯一标识
    if "user_uuid" not in st.session_state:
        st.session_state.user_uuid = uuid.uuid4().hex[:8]

    # 系统实例（每个用户独立）
    if "system" not in st.session_state:
        st.session_state.system = None

    # 对话历史（每个用户独立）
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 当前阶段：welcome, assessment, completed
    if "stage" not in st.session_state:
        st.session_state.stage = "welcome"

    # 最终结果
    if "final_result" not in st.session_state:
        st.session_state.final_result = None


# ==================== 欢迎页面 ====================
def render_welcome_page():
    """渲染欢迎页面"""

    # 顶部标题
    st.markdown("<h1 style='text-align: center;'>☆ CCTDI 批判性思维评估系统</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280; font-size: 1.1rem;'>基于AI的智能化批判性思维能力评估平台</p>",
                unsafe_allow_html=True)

    st.markdown("---")

    # 用户信息输入区
    st.markdown("### 👤 用户信息")

    col1, col2 = st.columns(2)
    with col1:
        user_id = st.text_input(
            "用户学号（必填，用于发放酬劳）*",
            value="",
            placeholder="请输入您的学号",
            help="必填项：用于识别和保存您的评估结果"
        )
    with col2:
        user_name = st.text_input(
            "姓名（必填）*",
            value="",
            placeholder="请输入您的姓名",
            help="必填项：用于识别和保存您的评估结果"
        )

    st.markdown("---")

    # 评估说明
    st.markdown("### 📋 评估说明")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**📊 7个维度**\n\n寻找真理、开放思想、分析能力、系统化能力、批判性思维自信、求知欲、认知成熟度")
    with col2:
        st.info("**⏱️ 评估时间**\n\n预计用时：15-25分钟\n每个维度3-5轮对话")
    with col3:
        st.info("**💡 温馨提示**\n\n请尽量详细回答\n越详细评估越准确")

    st.markdown("---")

    # 开始按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 开始评估", type="primary", use_container_width=True):
            # 验证必填字段
            if not user_id or not user_id.strip():
                st.error("⚠️ 请填写学号！学号是必填项，用于发放酬劳。")
                st.stop()

            if not user_name or not user_name.strip():
                st.error("⚠️ 请填写姓名！姓名是必填项。")
                st.stop()

            # 创建系统实例（每个用户独立）
            with st.spinner("正在初始化评估系统..."):
                st.session_state.system = CCTDIAssessmentSystem(
                    user_id=user_id.strip(),
                    user_name=user_name.strip()
                )

                # 开始评估
                result = st.session_state.system.start_assessment()

                # 添加系统首条消息
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"**📖 当前维度：{result['current_dimension']}**\n\n{result['first_question']}",
                    "mode": "正常"
                })

                # 切换到评估阶段
                st.session_state.stage = "assessment"
                st.rerun()


# ==================== 评估页面 ====================
def render_assessment_page():
    """渲染评估页面"""

    system = st.session_state.system

    # 获取当前状态
    current_dim = system.system_state.get("current_dimension", 1)
    completed = len(system.system_state.get("dimension_scores", {}))
    progress = (completed / 7) * 100

    # 顶部进度显示
    st.markdown("### 📊 评估进度")
    st.progress(progress / 100)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("当前维度", f"{current_dim}/7")
    with col2:
        st.metric("已完成", f"{completed}个维度")
    with col3:
        st.metric("进度", f"{progress:.0f}%")
    with col4:
        dimension_names = ["寻找真理", "开放思想", "分析能力", "系统化能力",
                          "批判性思维自信", "求知欲", "认知成熟度"]
        current_dim_name = dimension_names[current_dim - 1] if current_dim <= 7 else "完成"
        st.metric("当前", current_dim_name)

    st.markdown("---")

    # 显示已完成维度的得分（如果有）
    if completed > 0:
        with st.expander("📈 查看已完成维度得分", expanded=False):
            for dim_id, score_info in system.system_state["dimension_scores"].items():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{score_info['dimension']}**")
                with col2:
                    st.write(f"{score_info['score']}分 ({score_info['level']})")

    st.markdown("---")

    # 对话历史显示
    st.markdown("### 💬 对话记录")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and "mode" in msg:
                st.caption(f"🤖 {msg['mode']}模式")
            st.markdown(msg["content"])

    # 用户输入
    user_input = st.chat_input("💭 请输入您的回答...")

    if user_input:
        # 显示用户消息
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        # 处理用户回应
        with st.spinner("🤔 AI正在分析您的回答..."):
            result = system.process_user_response(user_input)

        # 根据结果类型处理
        if result.get("status") == "continue":
            # 继续当前维度对话
            st.session_state.messages.append({
                "role": "assistant",
                "content": result['next_question'],
                "mode": result['interaction_mode']
            })
            st.rerun()

        elif result.get("status") == "dimension_completed":
            # 当前维度完成，进入下一维度
            prev = result["previous_dimension_result"]
            new = result["new_dimension"]

            # 添加维度完成消息
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"✅ **{prev['name']} 维度评估完成！**\n\n📊 得分：{prev['score']}分\n🏆 评级：{prev['level']}\n\n---\n\n🎯 开始新维度：**{new['name']}** ({result['progress']})"
            })

            # 添加新维度首个问题
            st.session_state.messages.append({
                "role": "assistant",
                "content": new['first_question'],
                "mode": "正常"
            })
            st.rerun()

        elif result.get("status") == "completed":
            # 所有维度完成
            st.session_state.final_result = result
            st.session_state.stage = "completed"
            st.rerun()

        elif "error" in result:
            # 错误处理
            st.error(f"❌ {result['error']}")


# ==================== 完成页面 ====================
def render_completion_page():
    """渲染评估完成页面"""

    result = st.session_state.final_result

    # 顶部庆祝
    st.markdown("<h1 style='text-align: center;'>🎉 评估完成！</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280; font-size: 1.1rem;'>恭喜您完成了全部7个维度的评估</p>",
                unsafe_allow_html=True)

    st.markdown("---")

    # 总分展示
    st.markdown("### 📊 总体评估结果")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总分", f"{result['total_score']}/420")
    with col2:
        st.metric("平均分", f"{result['average_score']}")
    with col3:
        st.metric("总体评级", result['overall_level'])
    with col4:
        # 计算完成时间
        st.metric("已完成", "7/7 维度")

    # 总分进度条
    total_progress = result['total_score'] / 420
    st.progress(total_progress)

    st.markdown("---")

    # 各维度详细得分
    st.markdown("### 📈 各维度详细得分")

    dimension_names = ["寻找真理", "开放思想", "分析能力", "系统化能力",
                      "批判性思维自信", "求知欲", "认知成熟度"]

    for dim_id in range(1, 8):
        if dim_id in result["dimension_scores"]:
            score_info = result["dimension_scores"][dim_id]

            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                st.markdown(f"**{score_info['dimension']}**")

            with col2:
                # 进度条（满分60）
                progress = score_info['score'] / 60
                st.progress(progress)

            with col3:
                st.metric("", f"{score_info['score']}分")
                st.caption(score_info['level'])

            # 评分详情（可展开）
            with st.expander(f"查看 {score_info['dimension']} 详细评分"):
                st.markdown(f"**评分理由：**\n{score_info.get('reasoning', '暂无')}")
                if 'strengths' in score_info and score_info['strengths']:
                    st.markdown("**优势：**")
                    for strength in score_info['strengths']:
                        st.markdown(f"- {strength}")
                if 'weaknesses' in score_info and score_info['weaknesses']:
                    st.markdown("**改进建议：**")
                    for weakness in score_info['weaknesses']:
                        st.markdown(f"- {weakness}")

    st.markdown("---")

    # 数据文件信息
    st.markdown("### 📄 评估数据")

    session_id = result['session_id']

    st.info(f"""
    **您的评估数据已自动保存：**

    - 📝 对话记录：`data_real/conversations/{session_id}_对话.csv`
    - 📊 评估报告：`data_real/assessments/{session_id}_证据_思维.json`
    - 📋 评分汇总：`data_real/user_scores.csv`

    所有数据保存在本地，安全可靠。
    """)

    st.markdown("---")

    # 操作按钮
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("🔄 重新评估", use_container_width=True):
            # 清空所有会话状态
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with col2:
        # 下载JSON报告
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 下载JSON报告",
            data=json_data,
            file_name=f"{session_id}_评估报告.json",
            mime="application/json",
            use_container_width=True
        )

    with col3:
        st.markdown("[📖 了解更多](https://github.com)", unsafe_allow_html=True)


# ==================== 主函数 ====================
def main():
    """主函数 - 应用入口"""

    # 加载自定义样式
    load_custom_css()

    # 初始化会话状态
    initialize_session_state()

    # 根据当前阶段渲染页面
    if st.session_state.stage == "welcome":
        render_welcome_page()
    elif st.session_state.stage == "assessment":
        render_assessment_page()
    elif st.session_state.stage == "completed":
        render_completion_page()


# ==================== 程序入口 ====================
if __name__ == "__main__":
    main()
