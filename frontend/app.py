# -*- coding: utf-8 -*-
# @File Name:     app
# @Author :       Jun
# @Date:          2024/12/19
# @Description :
import pathlib
import requests
import json
import time
from typing import Generator

import streamlit as st

from examples import examples


def mermaid_chat(code: str) -> str:
    template = pathlib.Path("mermaid.template.html").read_text()
    return template.replace("{% code %}", code)


# Agent服务配置
AGENT_SERVICE_URL = "http://127.0.0.1:8503"  # Agent服务地址
DEFAULT_SESSION_ID = "streamlit-session"


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

        response = requests.post(url, json=payload, timeout=30)
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
    st.session_state.messages = []
    # 添加初始AI欢迎消息
    st.session_state.messages.append(
        {
            "role": "ai",
            "content": "我是跨区域人员流动量预测助手，可以帮助您分析出行流量、预测拥堵情况、解释模型结果。",
        }
    )

# 侧边栏
with st.sidebar:

    # 清空聊天历史按钮
    if st.button("🗑️ 清空聊天记录", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.example_question = None
        st.rerun()

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
