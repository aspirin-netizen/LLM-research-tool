import json
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import google.generativeai as genai
from datetime import datetime

# =========================
# 0) 固定配置（无需你改）
# =========================
SPREADSHEET_ID = "12xb05UFiwHE4gbfBMlmLmBmRvKmegpysk4JRutIF-Dw"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =========================
# 1) 认证 + 写入 Google Sheets（绕过 streamlit-gsheets & TOML 私钥坑）
# =========================
@st.cache_resource
def _get_gspread_client():
    """
    Secrets 里放：
    GSHEETS_SA_JSON = \"\"\"{...整份service account json...}\"\"\"
    不需要你改 \n
    """
    raw = st.secrets["GSHEETS_SA_JSON"]
    info = json.loads(raw)

    # 保险：如果某些环境把换行弄成了 \\n，这里在内存中修复一次（不改 toml）
    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def append_row_to_sheet(row: list):
    """
    直接写到第一个工作表（gid=0 对应的那一页）
    表头：Timestamp | Student_ID | Input | Output
    """
    gc = _get_gspread_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.get_worksheet(0)  # 第一个 tab
    ws.append_row(row, value_input_option="RAW")

# =========================
# 2) Streamlit 页面
# =========================
st.set_page_config(page_title="语言协作实证平台", layout="centered")

student_id = st.query_params.get("id", "Unknown_Student")

st.title("🎓 语言学习与人机协作研究")
st.markdown(f"**参与者编号：** `{student_id}`")
st.divider()

# =========================
# 3) 配置 AI 模型（Gemini）
# =========================
model = None
try:
    if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 你原来用的模型名我保留；如报模型不存在，再改成你账户可用的
        model = genai.GenerativeModel("models/gemini-3-flash-preview")
    else:
        st.error("缺少 GEMINI_API_KEY（请在 Secrets 中添加）")
except Exception as e:
    st.error(f"AI 加载失败: {e}")

# =========================
# 4) 对话与存档
# =========================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("在此输入翻译内容...")

if prompt:
    # 显示用户输入
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 生成并显示 AI 回复
    with st.chat_message("assistant"):
        if model is None:
            st.error("AI 模型未就绪，无法生成回复。")
        else:
            try:
                response = model.generate_content(prompt)
                ai_reply = getattr(response, "text", "") or ""
                st.markdown(ai_reply)
                st.session_state["messages"].append({"role": "assistant", "content": ai_reply})

                # 写入 Google Sheet（最稳的 gspread 方式）
                try:
                    row = [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        student_id,
                        prompt,
                        ai_reply,
                    ]
                    append_row_to_sheet(row)
                    st.toast("✅ 数据已同步至云端", icon="💾")
                except Exception as sheet_err:
                    st.error(f"写入表格失败：{sheet_err}")

            except Exception as e:
                st.error(f"AI 呼叫失败: {e}")
