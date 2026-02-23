import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 实验平台基础设置 ---
st.set_page_config(page_title="语言协作实证平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 核心：数据库连接 (含自动清洗逻辑) ---
@st.cache_resource
def get_secure_connection():
    try:
        # 1. 直接读取 Secrets
        s = st.secrets["connections"]["gsheets"].to_dict()
        # 2. 【核心修复】：无论 Secrets 里贴成什么样，代码强行将其中的 \n 替换为真换行
        # 这是为了解决困扰您一整天的 Unable to load PEM file 报错
        if "private_key" in s:
            s["private_key"] = s["private_key"].replace("\\n", "\n").strip()
        
        # 3. 建立连接
        return st.connection("gsheets", type=GSheetsConnection, **s)
    except Exception as e:
        st.error(f"⚠️ 数据库初始化中，请稍后。报错详情: {e}")
        return None

conn = get_secure_connection()

# --- 3. 配置 AI 模型 (2026 稳定版) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-3-flash-preview')
    except Exception as e:
        st.error(f"AI 加载失败: {e}")

# 对话与存档逻辑
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("在此输入翻译内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # --- 自动存入 Google Sheets (匹配表头: Timestamp, Student_ID, Input, Output) ---
            if conn is not None:
                try:
                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Student_ID": student_id,
                        "Input": prompt,
                        "Output": ai_reply
                    }])
                    conn.create(data=new_row)
                    st.toast("✅ 数据已同步至云端语料库", icon='💾')
                except Exception as sheet_err:
                    st.error(f"写入表格失败: {sheet_err}")
            else:
                st.warning("⚠️ 数据库连接未就绪，本次对话无法存档。")
                    
        except Exception as e:
            st.error(f"AI 响应异常: {e}")
