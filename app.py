import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="语言协作研究平台", layout="centered")

# 从 URL 参数获取学生 ID (例如 ?id=Student_01)，若无则显示 Unknown
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**当前参与者：** {student_id}")
st.caption("提示：在协作过程中，您可以随时向 AI 寻求翻译建议或反馈。")
st.divider()

# --- 2. 实验核心变量：系统指令 (针对口译/翻译研究优化) ---
SYSTEM_PROMPT = """
你是一位专业的口译导师与人工智能语言协作专家。
1. 请以专业、严谨且富有建设性的语气与学生交流。
2. 当学生提交译文时，请从“逻辑连贯性”、“术语准确性”及“表达地道度”三个维度给出具体建议。
3. 在协作中，鼓励学生发挥主体性，对你的建议进行批判性思考。
"""

# --- 3. 状态初始化 (防止之前的 AttributeError) ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 4. 连接数据库与 AI 模型 (2026 稳定版) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("数据库连接初始化中，请稍候...")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 使用您 2026 年可用列表中的最新型号
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction=SYSTEM_PROMPT
        )
    except Exception as e:
        st.error(f"模型初始化失败，请检查配置。错误详情：{e}")
else:
    st.warning("API Key 未配置，请在 Streamlit 后台设置 Secrets。")

# --- 5. 渲染聊天历史记录 ---
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 核心逻辑：对话互动与数据自动存证 ---
if prompt := st.chat_input("在此输入翻译内容或问题..."):
    # A. 记录学生输入
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # B. 异步获取 AI 回复
    with st.chat_message("assistant"):
        try:
            # 调用 2026 旗舰模型
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
