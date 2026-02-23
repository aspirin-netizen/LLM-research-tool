import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="语言协作研究平台", layout="centered")

# 从 URL 参数获取学生 ID
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**当前参与者：** {student_id}")
st.divider()

# --- 2. 实验核心变量：系统指令 ---
SYSTEM_PROMPT = """
你是一位专业的口译导师与人工智能语言协作专家。
1. 请以专业、严谨且富有建设性的语气与学生交流。
2. 当学生提交译文时，请从“逻辑连贯性”、“术语准确性”及“表达地道度”三个维度给出建议。
"""

# --- 3. 状态初始化 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 4. 配置数据库与 AI 模型 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库初始化中...")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 使用您 2026 年可用的最新型号
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction=SYSTEM_PROMPT
        )
    except Exception as e:
        st.error(f"模型配置失败: {e}")
else:
    st.warning("API Key 未配置。")

# --- 5. 渲染聊天历史 ---
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 核心互动与数据记录 ---
if prompt := st.chat_input("在此输入内容..."):
    # 显示用户输入
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 获取 AI 回复并存入数据库
    with st.chat_message("assistant"):
        try:
            # 1. 呼叫 AI
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # 2. 尝试将数据存入 Google Sheets
            try:
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=new_row)
            except Exception as e:
                st.caption(f"数据记录提醒: {e}")
                
        except Exception as e:
            st.error(f"AI 对话失败，请检查 API 状态。错误详情: {e}")
