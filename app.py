import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="语言协作研究平台", layout="centered")

# 获取学生 ID
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**当前参与者：** {student_id}")

# --- 2. 状态初始化 (防止 AttributeError) ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 3. 实验指令 ---
SYSTEM_PROMPT = "你是一名专业的口译导师，请协助学生。重点关注译文的逻辑和地道度。"

# --- 4. 配置模型 (使用确认可用的 2.0 Flash) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
    model_name='models/gemini-3-flash-preview', 
    system_instruction=SYSTEM_PROMPT
)

# --- 5. 显示聊天记录 ---
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 核心互动逻辑 ---
if prompt := st.chat_input("在此输入内容..."):
    # 显示学生输入
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. 尝试获取 AI 回复
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # B. 只有 AI 回复成功后，才尝试存入 Google 表格
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Role": "Interaction",
                    "Content": f"Student: {prompt} | AI: {ai_reply}"
                }])
                conn.create(data=new_row)
            except Exception as sheet_e:
                # 表格存不进去时，只显示小黄条警告，不中断对话
                st.warning(f"数据存入表格失败（AI已回复）：{sheet_e}")
                
        except Exception as ai_e:
            # 关键：这里会显示到底为什么 AI 不说话！
            st.error(f"AI 呼叫失败。错误详情：{ai_e}")
