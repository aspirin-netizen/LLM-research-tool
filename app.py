import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 页面配置
st.set_page_config(page_title="语言协作研究平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# 2. 数据库连接
conn = None
try:
    # 强制重新建立连接，确保读取最新 Secrets
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接失败: {e}")

# 3. AI 模型配置
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 渲染历史对话
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# 4. 对话与存证逻辑
if prompt := st.chat_input("在此输入翻译内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
        
        # 自动存入 Google Sheets
        if conn is not None:
            try:
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=new_row)
                st.toast("✅ 数据同步成功", icon='💾')
            except Exception as e:
                st.warning(f"⚠️ 写入表格失败: {e}")
