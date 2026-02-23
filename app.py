import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import traceback

# --- 1. 页面配置与受试者 ID 获取 ---
st.set_page_config(page_title="人机协作实证研究平台", layout="centered")

# 获取参数 ?id=XXX，用于 8 周实验的数据追踪
student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# --- 2. 实验核心变量 (System Instruction) ---
SYSTEM_PROMPT = """
你是一位专业的口译导师。
1. 请针对学生译文的逻辑、术语及表达地道度提供即时反馈。
2. 鼓励学生对 AI 的建议进行批判性思考，以提升其在算法中介下的互动胜任力。
"""

# --- 3. 初始化对话状态 ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- 4. 初始化数据库连接与 AI 模型 ---
try:
    # 建立 Google Sheets 连接
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库初始化失败，请检查 Secrets 配置: {e}")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 使用 2026 年最新旗舰模型 Gemini 3 Flash
        model = genai.GenerativeModel(
            model_name='models/gemini-3-flash-preview', 
            system_instruction=SYSTEM_PROMPT
        )
    except Exception as e:
        st.error(f"AI 模型启动失败: {e}")
else:
    st.warning("API Key 未配置。")

# --- 5. 渲染历史记录 ---
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 核心互动逻辑 ---
if prompt := st.chat_input("请在此输入您的翻译内容..."):
    # 记录学生输入
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 呼叫 AI 获取协作反馈
    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            ai_reply = response.text
            st.markdown(ai_reply)
            st.session_state["messages"].append({"role": "assistant", "content": ai_reply})
            
            # --- 自动存证：将协作语料写入 Google Sheets ---
            try:
                # 按照您设定的表头：Timestamp, Student_ID, Input, Output
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": student_id,
                    "Input": prompt,
                    "Output": ai_reply
                }])
                
                # 执行写入操作
                conn.create(data=new_row)
                st.toast("💾 协作数据已成功同步至后台", icon='✅')
                
            except Exception:
                # 若写入失败，显示详细报错以供排查私钥格式
                st.error("⚠️ 语料自动同步失败")
                with st.expander("查看底层报错（用于排查私钥格式）"):
                    st.code(traceback.format_exc())
                
        except Exception as ai_err:
            st.error(f"AI 响应中断: {ai_err}")
