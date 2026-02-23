import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 基础配置
st.set_page_config(page_title="人机协作实证研究平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# 2. 数据库连接初始化
conn = None
try:
    # 建立 Google Sheets 连接
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库认证失败，请检查 Secrets 配置。详情: {e}")

# 3. AI 模型配置
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 使用 2026 年最新旗舰模型 Gemini 3 Flash
        model = genai.GenerativeModel('models/gemini-3-flash-preview')
    except Exception as e:
        st.error(f"AI 模型加载失败: {e}")

# 4. 对话状态管理
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# 5. 互动逻辑与自动存档
if prompt := st.chat_input("在此输入翻译练习内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # AI 响应
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # 自动同步至 Google Sheets
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
                    
        except Exception as e:
            st.error(f"AI 呼叫异常: {e}")
