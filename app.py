import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import traceback

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="语言协作研究平台", layout="centered")

# 获取学生 ID (用于您的 8 周实验语料分类)
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**当前参与者：** {student_id}")
st.divider()

# --- 2. 实验系统指令 ---
SYSTEM_PROMPT = """
你是一位专业的口译导师。
1. 请针对译文的逻辑、术语和地道度提供反馈。
2. 鼓励学生在协作中提出见解。
"""

# --- 3. 状态初始化 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 4. 配置数据库与 AI 模型 ---
try:
    # 建立 Google Sheets 连接
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库初始化失败: {e}")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 使用 2026 年最新旗舰模型
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

# --- 6. 核心互动逻辑：对话与自动存证 ---
if prompt := st.chat_input("在此输入翻译内容..."):
    # 记录学生输入
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 获取 AI 回复
    with st.chat_message("assistant"):
        try:
            # 调用 AI
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # --- 自动存证区：写入 Google Sheets ---
            try:
                # 构造符合您表格表头的数据
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                
                # 写入表格
                conn.create(data=new_row)
                st.toast("💾 数据已成功同步至 Google Sheet", icon='✅')
                
            except Exception:
                # 记录详细的写入报错
                st.error("⚠️ 写入表格失败！")
                with st.expander("点击查看详细报错详情 (排查私钥格式)"):
                    st.code(traceback.format_exc())
                
        except Exception as ai_err:
            st.error(f"AI 呼叫失败: {ai_err}")
