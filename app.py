import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import traceback

# --- 1. 实验平台基础配置 ---
st.set_page_config(page_title="人机协作实证平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 核心修复：手动构建并修正数据库连接 ---
@st.cache_resource
def get_db_connection():
    # 从 Secrets 获取原始数据
    secrets_dict = dict(st.secrets["connections"]["gsheets"])
    # 【核心修复】：将粘贴过程中可能产生的错误转义字符强行修正为标准换行符
    # 彻底解决 "short data" 和 "Unable to load PEM file" 报错
    raw_key = secrets_dict.get("private_key", "")
    fixed_key = raw_key.replace("\\n", "\n").strip()
    secrets_dict["private_key"] = fixed_key
    
    # 使用修正后的字典建立连接
    return st.connection("gsheets", type=GSheetsConnection, **secrets_dict)

try:
    conn = get_db_connection()
except Exception as e:
    st.error(f"数据库认证失败，请检查 Secrets 配置。详情: {e}")

# --- 3. 配置 2026 旗舰模型 Gemini 3 Flash ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction="你是一位专业的口译导师。请针对译文的逻辑、术语及表达地道度提供反馈。"
        )
    except Exception as e:
        st.error(f"AI 模型初始化失败: {e}")

# --- 4. 互动与自动存证逻辑 ---
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
            # 呼叫 AI
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # 存入 Google Sheets (严格匹配您的表头: Timestamp, Student_ID, Input, Output)
            try:
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=new_row)
                st.toast("✅ 数据已同步至云端语料库", icon='💾')
            except Exception:
                st.error("⚠️ 协作数据同步失败")
                with st.expander("查看底层报错（用于协助排查）"):
                    st.code(traceback.format_exc())
                    
        except Exception as e:
            st.error(f"AI 响应异常: {e}")
