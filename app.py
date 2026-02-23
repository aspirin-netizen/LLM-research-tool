import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 实验平台基础设置 ---
st.set_page_config(page_title="语言协作实证平台", layout="centered")
# 获取受试者 ID，用于 8 周实验分类
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 核心：数据库连接 (含自动纠错逻辑) ---
@st.cache_resource
def get_secure_connection():
    try:
        # 获取原始 Secrets 字典
        s = st.secrets["connections"]["gsheets"].to_dict()
        # 【核心修复】：无论用户怎么粘贴私钥，代码强行将其中的 \n 替换为标准换行符
        if "private_key" in s:
            s["private_key"] = s["private_key"].replace("\\n", "\n").strip()
        
        # 建立带清洗后私钥的连接
        return st.connection("gsheets", type=GSheetsConnection, **s)
    except Exception as e:
        st.error(f"⚠️ 数据库配置待完善。详情: {e}")
        return None

conn = get_secure_connection()

# --- 3. 配置 AI 模型 (2026 稳定版) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction="你是一位专业的口译导师。请针对译文的逻辑、术语及表达地道度提供反馈。"
        )
    except Exception as e:
        st.error(f"AI 模型初始化失败: {e}")

# --- 4. 互动逻辑与自动存档 ---
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
            
            # 自动存证逻辑：只有在连接成功时执行
            if conn is not None:
                try:
                    # 严格匹配您的表头: Timestamp, Student_ID, Input, Output
                    new_row = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Student_ID": student_id,
                        "Input": prompt,
                        "Output": ai_reply
                    }])
                    conn.create(data=new_row)
                    st.toast("✅ 数据已同步至云端语料库", icon='💾')
                except Exception as sheet_err:
                    st.error(f"数据写入失败: {sheet_err}")
            else:
                st.warning("⚠️ 数据库未就绪，本次对话无法存档。")
                    
        except Exception as e:
            st.error(f"AI 呼叫异常: {e}")
