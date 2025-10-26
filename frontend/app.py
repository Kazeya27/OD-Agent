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


def call_agent_service(question: str, session_id: str = DEFAULT_SESSION_ID) -> str:
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
    session_id: str = DEFAULT_SESSION_ID,
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

# 初始化聊天历史
if "messages" not in st.session_state:
    # 尝试从本地加载聊天记录
    saved_messages = chat_storage.load_chat(DEFAULT_SESSION_ID)
    if saved_messages:
        st.session_state.messages = saved_messages
    else:
        st.session_state.messages = []
        # 添加初始AI欢迎消息
        st.session_state.messages.append(
            {
                "role": "ai",
                "content": "我是跨区域人员流动量预测助手，可以帮助您分析出行流量、预测拥堵情况、解释模型结果。",
            }
        )
        # 保存初始消息
        chat_storage.save_chat(DEFAULT_SESSION_ID, st.session_state.messages)

# 侧边栏
with st.sidebar:

    # 清空聊天历史按钮
    if st.button("🗑️ 清空聊天记录", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.example_question = None
        # 清空本地存储
        chat_storage.delete_session(DEFAULT_SESSION_ID)
        st.rerun()

    st.divider()

    # 聊天记录管理
    st.subheader("💾 聊天记录管理")

    # 显示当前会话信息
    message_count = len(st.session_state.messages)
    st.info(f"当前会话消息数: {message_count}")

    # 获取所有会话
    all_sessions = chat_storage.get_all_sessions()
    if all_sessions:
        st.write("历史会话:")
        for session in all_sessions[:5]:  # 只显示最近5个会话
            session_id = session["session_id"]
            message_count = session["message_count"]
            updated_at = session.get("updated_at", "")
            if updated_at:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(updated_at)
                    time_str = dt.strftime("%m-%d %H:%M")
                except:
                    time_str = updated_at[:16]
            else:
                time_str = "未知时间"

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📝 {message_count}条消息 ({time_str})")
            with col2:
                if st.button("🗑️", key=f"del_{session_id}", help="删除此会话"):
                    if chat_storage.delete_session(session_id):
                        st.success("会话已删除")
                        st.rerun()
                    else:
                        st.error("删除失败")

    st.divider()

    st.subheader("📋 选择一个示例")
    for k, v in examples.items():
        if st.button(k, key=k, use_container_width=True):
            # 使用st.rerun()来刷新页面并设置新的用户输入
            st.session_state.example_question = v
            st.rerun()


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

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(name=message["role"]):
        st.write(message["content"])

# 处理用户问题
if user_question:
    # 添加用户消息到历史
    st.session_state.messages.append({"role": "user", "content": user_question})
    # 保存用户消息到本地
    chat_storage.save_chat(DEFAULT_SESSION_ID, st.session_state.messages)

    # 显示用户消息
    with st.chat_message(name="user"):
        st.write(user_question)

    # 生成AI回答
    with st.chat_message(name="ai"):
        with st.status(label="正在生成分析结果", state="running"):
            answer = call_agent_service(user_question, DEFAULT_SESSION_ID)
        st.success("分析结果生成成功")
        st.markdown(answer)

        # 添加AI回答到历史
        st.session_state.messages.append({"role": "ai", "content": answer})
        # 保存AI回答到本地
        chat_storage.save_chat(DEFAULT_SESSION_ID, st.session_state.messages)
