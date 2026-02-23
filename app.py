import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 页面基础配置
st.set_page_config(page_title="语言协作实证平台", layout="centered")
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 核心：数据库连接初始化 ---
# 预定义 conn 为 None，防止出现 NameError
conn = None

try:
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        # 获取 Secrets 字典并深度清洗私钥中的反斜杠
        secrets_dict = dict(st.secrets["connections"]["gsheets"])
        raw_key = secrets_dict.get("private_key", "")
        # 将文本形式的 \n 转换为真实的换行符，这是解决所有 PEM 报错的关键
        fixed_key = raw_key.replace("\\n", "\n").strip()
        secrets_dict["private_key"] = fixed_key
        
        # 建立连接
        conn = st.connection("gsheets", type=GSheetsConnection, **secrets_dict)
except Exception as e:
    st.error(f"⚠️ 数据库初始化失败，请核对 Secrets 格式。详情: {e}")

# --- 配置 AI 模型 (2026 旗舰版) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction="你是一位专业的口译导师。请针对译文的逻辑、术语及表达地道度提供反馈。"
        )
    except Exception as e:
        st.error(f"模型配置失败: {e}")

# 对话状态管理
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 互动逻辑
if prompt := st.chat_input("在此输入您的翻译练习内容..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # AI 响应
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # 安全写入逻辑：只有当 conn 成功创建时才尝试写入，防止崩溃
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
                st.warning("⚠️ 数据库连接未就绪，本次对话仅在本地显示，无法存档。")
                    
        except Exception as e:
            st.error(f"AI 呼叫异常: {e}")
