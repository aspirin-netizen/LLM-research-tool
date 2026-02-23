import base64
import json
import traceback
import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials
import streamlit as st
import google.generativeai as genai
from datetime import datetime

# =========================
# 0) 固定配置（你的 Google Sheet）
# =========================
SPREADSHEET_ID = "12xb05UFiwHE4gbfBMlmLmBmRvKmegpysk4JRutIF-Dw"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =========================
# 1) 认证 + 写入 Google Sheets（读取 Secrets 里的 base64）
# =========================
@st.cache_resource
def _get_gspread_client():
    b64 = st.secrets.get("GSHEETS_SA_JSON_B64", "")
    if not b64:
        raise RuntimeError('Secrets 缺少 "GSHEETS_SA_JSON_B64"（请在 App settings → Secrets 里添加）')

    raw = base64.b64decode(b64).decode("utf-8")
    info = json.loads(raw)

    # 保险：如果 private_key 变成了 \\n，这里只在内存里修复
    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()

    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def append_row_to_sheet(row: list):
    """
    写入：Timestamp | Student_ID | Input | Output
    返回 (ok: bool, err: str|None)
    """
    try:
        gc = _get_gspread_client()
        sh = gc.open_by_key(SPREADSHEET_ID)

        # 更稳：直接写默认的第一个工作表
        ws = sh.sheet1

        ws.append_row(row, value_input_option="RAW")
        return True, None

    except APIError as e:
        return False, f"APIError: {repr(e)}"

    except Exception as e:
        tb = traceback.format_exc()
        return False, f"{repr(e)}\n\nTRACEBACK:\n{tb}"

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
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("缺少 GEMINI_API_KEY（请在 Secrets 中添加）")
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-3-flash-preview")
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
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if model is None:
            st.error("AI 模型未就绪，无法生成回复。")
        else:
            try:
                response = model.generate_content(prompt)
                ai_reply = getattr(response, "text", "") or ""
                st.markdown(ai_reply)
                st.session_state["messages"].append({"role": "assistant", "content": ai_reply})

                ok, err = append_row_to_sheet([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    student_id,
                    prompt,
                    ai_reply
                ])

                if ok:
                    st.toast("✅ 数据已同步至云端", icon="💾")
                else:
                    st.error("写入表格失败（真实错误如下）:")
                    st.code(err)

            except Exception as e:
                st.error(f"AI 呼叫失败: {e}")
