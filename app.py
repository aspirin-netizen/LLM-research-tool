import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="人机协作实证研究", layout="centered")
student_id = st.query_params.get("id", "Unknown")

st.title("🎓 语言协作研究平台")

# --- 核心：手动解析 JSON 钥匙 ---
@st.cache_resource
def get_conn():
    try:
        # 直接读取原始字符串
        raw_json = st.secrets["RAW_GCP_JSON"]
        # 强制处理可能存在的双重转义
        clean_json = raw_json.replace('\\\\n', '\\n')
        conf = json.loads(clean_json)
        
        # 建立连接
        return st.connection("gsheets", type=GSheetsConnection, **conf)
    except Exception as e:
        st.error(f"❌ 认证解析失败: {e}")
        return None

conn = get_conn()

# --- AI 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("输入翻译练习内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
        
        # --- 自动同步 ---
        if conn is not None:
            try:
                # 匹配表头 Timestamp, Student_ID, Input, Output
                new_data = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Student_ID": student_id, "Input": prompt, "Output": ai_reply}])
                conn.create(data=new_data)
                st.success("✅ 数据已写入表格")
            except Exception as e:
                # 如果失败，这里会吐出具体的 Google 报错（比如：权限不足、API 未开启）
                st.warning(f"⚠️ 对话成功但存档失败: {e}")
