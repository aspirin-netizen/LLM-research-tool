import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import traceback

# --- 1. 实验基本配置 ---
st.set_page_config(page_title="人机协作科研平台", layout="centered")

# 获取受试者 ID
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 核心：数据库与 AI 配置 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库初始化中，请检查 Secrets: {e}")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 使用您账户可用的最新 3.0 模型
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction="你是一位专业的口译导师，请针对译文逻辑和地道度提供建议。"
        )
    except Exception as e:
        st.error(f"模型加载失败: {e}")

# --- 3. 对话与存证逻辑 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("在此输入您的翻译练习内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # --- 自动存证：写入 Google Sheets ---
            try:
                # 严格对应表格表头: Timestamp, Student_ID, Input, Output
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=new_row)
                st.toast("✅ 数据已同步至语料库", icon='💾')
            except Exception:
                st.error("⚠️ 写入失败！")
                with st.expander("查看底层报错（用于排查私钥格式）"):
                    st.code(traceback.format_exc())
                    
        except Exception as e:
            st.error(f"AI 呼叫异常: {e}")
