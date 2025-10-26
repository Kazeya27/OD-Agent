# -*- coding: utf-8 -*-
# @File Name:     app
# @Author :       Jun
# @Date:          2024/12/19
# @Description :
import pathlib
import requests
import os
from typing import Generator
from dotenv import load_dotenv

import streamlit as st

from examples import examples
from chat_storage import ChatStorage

# 加载环境变量
load_dotenv()


def mermaid_chat(code: str) -> str:
    template = pathlib.Path("mermaid.template.html").read_text()
    return template.replace("{% code %}", code)


# Agent服务配置
AGENT_SERVICE_URL = os.getenv(
    "AGENT_SERVICE_URL", "http://127.0.0.1:8503"
)  # Agent服务地址

# 初始化聊天存储
chat_storage = ChatStorage()


def call_agent_service(question: str, session_id: str) -> str:
    """
    调用agent服务获取回答

    Args:
        question: 用户问题
        session_id: 会话ID

    Returns:
        agent的回答
    """
    try:
        url = f"{AGENT_SERVICE_URL}/chat"
        payload = {"session_id": session_id, "question": question}

        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()

        result = response.json()
        return result.get("answer", "抱歉，无法获取回答。")

    except requests.exceptions.RequestException as e:
        return f"连接agent服务失败: {str(e)}"
    except Exception as e:
        return f"处理请求时出错: {str(e)}"


def call_agent_service_stream(
    question: str,
    session_id: str,
) -> Generator[str, None, None]:
    """
    流式调用agent服务获取回答

    Args:
        question: 用户问题
        session_id: 会话ID

    Yields:
        回答的文本片段
    """
    try:
        # 直接获取完整回答，不使用模拟流式
        answer = call_agent_service(question, session_id)
        yield answer

    except Exception as e:
        yield f"错误: {str(e)}"


st.set_page_config(page_title="OD流量预测", page_icon="🚗", layout="wide")

st.title("全社会跨区域人员流动量预测智能体")

# 初始化会话状态
if "current_session_id" not in st.session_state:
    # 总是创建新的对话标签页作为默认显示
    first_session_id = chat_storage.create_new_session("新对话")
    st.session_state.current_session_id = first_session_id

if "sessions" not in st.session_state:
    st.session_state.sessions = {}

# 获取当前会话的消息
current_session_id = st.session_state.current_session_id
if current_session_id not in st.session_state.sessions:
    # 从存储加载消息
    saved_messages = chat_storage.load_chat(current_session_id)
    st.session_state.sessions[current_session_id] = saved_messages

current_messages = st.session_state.sessions[current_session_id]

# 侧边栏 - 标签页管理
with st.sidebar:
    st.subheader("📑 对话标签页")

    # 创建新标签页按钮
    if st.button("➕ 新建对话", use_container_width=True, type="primary"):
        new_session_id = chat_storage.create_new_session()
        if new_session_id:
            st.session_state.current_session_id = new_session_id
            st.session_state.sessions[new_session_id] = chat_storage.load_chat(
                new_session_id
            )
            st.rerun()

    st.divider()

    # 显示所有标签页
    all_sessions = chat_storage.get_all_sessions()
    if all_sessions:
        for session in all_sessions:
            session_id = session["session_id"]
            session_name = session.get("session_name", f"对话_{session_id}")
            message_count = session["message_count"]
            updated_at = session.get("updated_at", "")

            # 格式化时间
            if updated_at:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(updated_at)
                    time_str = dt.strftime("%m-%d %H:%M")
                except:
                    time_str = updated_at[:16]
            else:
                time_str = "未知时间"

            # 标签页选择
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                # 当前标签页高亮显示
                if session_id == current_session_id:
                    st.button(
                        f"📌 {session_name}",
                        key=f"tab_{session_id}",
                        use_container_width=True,
                        disabled=True,
                    )
                else:
                    if st.button(
                        f"📄 {session_name}",
                        key=f"tab_{session_id}",
                        use_container_width=True,
                    ):
                        st.session_state.current_session_id = session_id
                        if session_id not in st.session_state.sessions:
                            st.session_state.sessions[session_id] = (
                                chat_storage.load_chat(session_id)
                            )
                        st.rerun()

            with col2:
                st.caption(f"{message_count}条")

            with col3:
                if st.button("🗑️", key=f"del_{session_id}", help="删除此标签页"):
                    if chat_storage.delete_session(session_id):
                        # 如果删除的是当前标签页，切换到第一个标签页
                        if session_id == current_session_id:
                            remaining_sessions = [
                                s for s in all_sessions if s["session_id"] != session_id
                            ]
                            if remaining_sessions:
                                st.session_state.current_session_id = (
                                    remaining_sessions[0]["session_id"]
                                )
                            else:
                                # 创建新的标签页
                                new_session_id = chat_storage.create_new_session()
                                st.session_state.current_session_id = new_session_id
                                st.session_state.sessions[new_session_id] = (
                                    chat_storage.load_chat(new_session_id)
                                )
                        # 从内存中删除
                        if session_id in st.session_state.sessions:
                            del st.session_state.sessions[session_id]
                        st.success("标签页已删除")
                        st.rerun()
                    else:
                        st.error("删除失败")

    st.divider()

    # 示例问题
    st.subheader("📋 选择一个示例")
    for k, v in examples.items():
        if st.button(k, key=k, use_container_width=True):
            st.session_state.example_question = v
            st.rerun()

# 主聊天区域
st.subheader(f"💬 {chat_storage.get_session_info(current_session_id)['session_name']}")

# 处理示例问题
if "example_question" in st.session_state and st.session_state.example_question:
    user_question = st.session_state.example_question
    st.session_state.example_question = None  # 清除示例问题标记
else:
    user_question = None

# 用户输入
prompt = st.chat_input("请输入您的问题：")
if prompt:
    user_question = prompt

# 显示当前标签页的聊天历史
for message in current_messages:
    with st.chat_message(name=message["role"]):
        st.write(message["content"])

# 处理用户问题
if user_question:
    # 添加用户消息到当前会话
    current_messages.append({"role": "user", "content": user_question})
    # 保存到存储
    chat_storage.save_chat(current_session_id, current_messages)
    # 更新内存中的会话
    st.session_state.sessions[current_session_id] = current_messages

    # 显示用户消息
    with st.chat_message(name="user"):
        st.write(user_question)

    # 生成AI回答
    with st.chat_message(name="ai"):
        with st.status(label="正在生成分析结果", state="running"):
            answer = call_agent_service(user_question, current_session_id)
        st.success("分析结果生成成功")
        st.markdown(answer)

        # 添加AI回答到当前会话
        current_messages.append({"role": "ai", "content": answer})
        # 保存到存储
        chat_storage.save_chat(current_session_id, current_messages)
        # 更新内存中的会话
        st.session_state.sessions[current_session_id] = current_messages
