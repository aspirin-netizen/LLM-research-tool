import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="语言协作研究平台", layout="centered")

# 从链接获取学生 ID (?id=S01)
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**当前参与者：** {student_id}")
st.caption("实验过程中，请像平时一样与 AI 协作完成任务。")
st.divider()

# --- 2. 实验核心变量：系统指令 ---
# 既然你研究口译与二语习得，这里是 AI 的“灵魂”
SYSTEM_PROMPT = """
你是一名专业的口译导师。你的任务是辅助学生。
1. 保持专业且具有建设性的反馈风格。
2. 重点关注译文的逻辑衔接和术语准确性。
3. 鼓励学生在协作中提出自己的见解。
"""

# --- 3. 稳健的初始化逻辑 (解决 AttributeError 的关键) ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 4. 连接数据库与模型 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("数据库初始化中...")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 使用你截图中确认可用的 2.0 Flash 模型
    model = genai.GenerativeModel(
        model_name='models/gemini-2.0-flash', 
        system_instruction=SYSTEM_PROMPT
    )
else:
    st.warning("API Key 未配置，请检查 Secrets 设置。")

# --- 5. 聊天界面显示 ---
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 互动与数据自动沉淀 ---
if prompt := st.chat_input("在此输入内容..."):
    # A. 记录学生话语并显示
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # B. 【静默存储】学生语料
    try:
        new_data = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Student_ID": student_id,
            "Role": "Student",
            "Content": prompt
        }])
        conn.create(data=new_data)
    except:
        pass

    # C. 获取 AI 回复
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # D. 【静默存储】AI 回复语料
            ai_data = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Student_ID": student_id,
                "Role": "AI_Tutor",
                "Content": ai_reply
            }])
            conn.create(data=ai_data)
        except Exception as e:
            st.error(f"对话发生错误，请刷新页面重试。")
