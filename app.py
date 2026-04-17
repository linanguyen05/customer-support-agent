# app.py
import json
import os
import re
from datetime import datetime
import streamlit as st
from retriever import PDFRetriever
from agent import Agent

st.set_page_config(page_title="Amazon Customer Agent", layout="wide")
st.title("Amazon E‑commerce Support Agent")
st.markdown("Hỏi về thông tin từ báo cáo Amazon 10-K hoặc kiểm tra trạng thái đơn hàng.")

CONVERSATION_DIR = "conversations"

def _mask_sensitive(text: str) -> str:
    if not isinstance(text, str):
        return text

    # Mask SSN last 4
    text = re.sub(r"(?i)(ssn(?:\s*last\s*4)?\s*(?:is|=|:)?\s*)(\d{4})", r"\1****", text)
    
    # Mask DOB in common patterns
    text = re.sub(r"(\d{4}-\d{2}-\d{2})", "****-**-**", text)
    
    # Mask order identity pattern
    text = re.sub(
        r"(\b[A-Za-z]+(?:\s+[A-Za-z]+)*\s*,\s*)(\d{4})(\s*,\s*\d{4}-\d{2}-\d{2}\b)",
        r"\1****\3", text
    )
    return text

def _save_conversation(history):
    os.makedirs(CONVERSATION_DIR, exist_ok=True)
    # Lưu vào một file cố định cho session hiện tại (hoặc dùng session id)
    file_path = os.path.join(CONVERSATION_DIR, "latest_conversation.json")
    
    sanitized = [
        {"role": msg.get("role"), "content": _mask_sensitive(msg.get("content", "")) if isinstance(msg.get("content"), str) else msg.get("content")}
        for msg in history
    ]
    payload = {
        "saved_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "messages": sanitized
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

@st.cache_resource
def init_retriever():
    return PDFRetriever()

if "agent" not in st.session_state:
    st.session_state.agent = Agent(init_retriever())

agent = st.session_state.agent

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

col1, col2 = st.columns([0.8, 0.2])
with col2:
    if st.button("🗑️ Clear history"):
        agent.clear_history()
        st.session_state.chat_history = []
        st.rerun()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi của bạn..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            response = agent.respond(prompt)
            st.markdown(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})

    _save_conversation(st.session_state.chat_history)
