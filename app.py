import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基础配置 ---
st.set_page_config(page_title="人机协作实证研究平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 数据库连接 ---
@st.cache_resource
def get_db():
    try:
        # 强制建立连接
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"❌ 数据库初始化失败，请核对 Secrets 格式：{e}")
        return None

conn = get_db()

# --- 3. AI 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# --- 4. 核心逻辑 ---
if prompt := st.chat_input("输入翻译练习内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        # AI 回复
        response = model.generate_content(prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
        
        # 自动存档：匹配表头 Timestamp, Student_ID, Input, Output
        if conn is not None:
            try:
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=new_row)
                st.success("✅ 数据已实时同步至 Google 表格")
            except Exception as e:
                st.warning(f"⚠️ 对话成功，但写入表格报错：{e}")
        else:
            st.warning("⚠️ 数据库连接未建立，本次数据无法存档。")
