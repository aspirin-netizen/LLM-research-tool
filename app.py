import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="数据同步诊断平台", layout="centered")

# 1. 核心：解析钥匙并连接
@st.cache_resource
def get_conn():
    try:
        # 自动读取并修正 JSON 格式
        raw_json = st.secrets["GCP_SERVICE_ACCOUNT_JSON"]
        # 修正可能存在的双重转义
        clean_json = raw_json.replace('\\\\n', '\\n')
        creds = json.loads(clean_json)
        
        # 强制修正私钥中的换行符（这是解决 InvalidByte 的终极手段）
        if "private_key" in creds:
            creds["private_key"] = creds["creds"].get("private_key", "").replace("\\n", "\n")
            
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    except Exception as e:
        st.error(f"❌ 认证初始化失败。请核对 Secrets 里的 JSON 字符串。详情: {e}")
        return None

conn = get_conn()

# 2. AI 模型配置
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-3-flash-preview')

# 3. 互动逻辑
if prompt := st.chat_input("输入内容进行同步测试..."):
    st.chat_message("user").markdown(prompt)
    with st.chat_message("assistant"):
        response = model.generate_content(prompt)
        ai_reply = response.text
        st.markdown(ai_reply)
        
        # 4. 尝试同步
        if conn is not None:
            try:
                # 按照表格表头：Timestamp, Student_ID, Input, Output
                df = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Student_ID": st.query_params.get("id", "Test_User"),
                    "Input": prompt,
                    "Output": ai_reply
                }])
                conn.create(data=df)
                st.success("✅ 数据已同步至 Google Sheets")
            except Exception as e:
                # 这里的报错会告诉我们：是 API 没开，还是表格没分享给 Service Account 邮箱
                st.warning(f"⚠️ 对话成功但存档失败。底层报错: {e}")
                if "403" in str(e):
                    st.info("提示：请检查是否已将表格分享给教学服务账号邮箱，并设为'编辑器'。")
