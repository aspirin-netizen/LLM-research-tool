import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import traceback

# --- 1. 页面配置 ---
st.set_page_config(page_title="语言协作实证平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 实验核心逻辑 ---
SYSTEM_PROMPT = "你是一位专业的口译导师。请针对译文的逻辑、术语及表达地道度提供反馈。"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 3. 初始化数据库连接 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("数据库连接配置中，请检查 Secrets。")

# --- 4. 配置模型 (2026 稳定版) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction=SYSTEM_PROMPT
        )
    except Exception as e:
        st.error(f"模型初始化失败: {e}")

# --- 5. 对话渲染 ---
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 核心：存证与互动 ---
if prompt := st.chat_input("在此输入您的翻译内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # A. 呼叫 AI
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # B. 存入 Google Sheets (严格匹配您的表头)
            try:
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=new_row)
                st.toast("✅ 数据已同步至云端", icon='💾')
            except Exception:
                st.error("⚠️ 写入表格失败！")
                with st.expander("查看技术报错（通常是私钥格式问题）"):
                    st.code(traceback.format_exc())
                    
        except Exception as e:
            st.error(f"AI 响应中断: {e}")
