import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 基础配置与学生ID获取
st.set_page_config(page_title="语言协作研究平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# 2. 初始化数据库连接
conn = None
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接初始化失败: {e}")

# 3. AI 模型配置 (2026 旗舰版)
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-3-flash-preview')
    except Exception as e:
        st.error(f"AI 模型加载失败: {e}")

# 对话历史管理
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# 4. 互动逻辑与存档
if prompt := st.chat_input("在此输入翻译练习内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # 获取 AI 回复
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # 自动存档逻辑
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
                    st.error(f"⚠️ 写入表格失败，请确认表格已分享给 {st.secrets['connections']['gsheets']['client_email']}。错误: {sheet_err}")
                    
        except Exception as e:
            st.error(f"AI 呼叫异常: {e}")
