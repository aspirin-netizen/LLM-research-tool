import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 页面基础设置 ---
st.set_page_config(page_title="语言协作研究工具", layout="centered")
query_params = st.query_params
student_id = query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**当前参与者：** {student_id}")
st.divider()

# --- 2. AI 的角色设定（你以后可以在这里修改研究变量） ---
SYSTEM_PROMPT = """
你是一位专业的语言教学专家和口译导师。你的任务是协助学生进行翻译或写作练习。
1. 请保持鼓励性的语气。
2. 当学生提交翻译时，请从逻辑、术语准确性和表达地道度三个维度给出建议。
"""

# --- 3. 连接数据库 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接中...")

# --- 4. 初始化 Gemini ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
    model_name='models/gemini-3-flash-preview',
        system_instruction=SYSTEM_PROMPT
    )
else:
    st.warning("API Key 尚未配置。")

# --- 5. 聊天记录管理 ---
# 修改后的初始化部分
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 尝试使用最稳定的名称
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash-latest', 
        system_instruction=SYSTEM_PROMPT
    )
else:
    st.warning("API Key 尚未配置。")

# --- 6. 核心：互动与实时存数据 ---
if prompt := st.chat_input("在此输入内容..."):
    # 显示学生输入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 【关键】将学生的话存入 Google 表格
    try:
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Student_ID": student_id, 
            "Role": "Student", 
            "Content": prompt
        }])
        conn.create(data=new_row)
    except:
        pass

    # 获取 AI 回复并显示
    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})

    # 【关键】将 AI 的话存入 Google 表格
    try:
        ai_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "Student_ID": student_id, 
            "Role": "AI_Tutor", 
            "Content": ai_reply
        }])
        conn.create(data=ai_row)
    except:
        pass
