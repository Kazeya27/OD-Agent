#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OD agent built on top of the backend HTTP API."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatTongyi

# Import tools from tools module
from tools import TOOLS, set_base_url

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")
load_dotenv(_HERE.parent / "backend" / ".env")

# ---------------------------------------------------------------------------
# LLM selection and prompts
# ---------------------------------------------------------------------------


def get_llm(provider: str, model_name: str, temperature: float = 0.0):
    """Get LLM instance based on provider."""
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            convert_system_message_to_human=True,
        )
    elif provider == "qwen":
        if ChatTongyi is None:
            raise RuntimeError("未安装 langchain_community，无法使用 Qwen")
        return ChatTongyi(
            model_name=model_name,
            temperature=temperature,
        )
    raise ValueError(f"不支持的 provider: {provider}")


TODAY_DATE = datetime.now().strftime("%Y-%m-%d")

SYSTEM_PROMPT = (
    "## 角色定义\\n"
    "你是一名严格、可靠的出行需求与城市/省级流动分析助手（OD Agent）。"
    "\\n"
    "## 领域知识：\\n"
    f"- 今天日期： {TODAY_DATE}\\n"
    "- 2025年春运期定义为：2025-01-26 至 2025-02-06\\n"
    "## 常见任务：\\n"
    "- 根据城市名查询 geo_id；\\n"
    "- 查询或预测OD对的人员流动情况。查询时使用获取真实值的工具，预测时使用获取预测值的工具\\n"
    "- 生成预测、计算增长率、评估误差指标；\\n"
    "- 调用分析接口获取省市流动与通道排名；\\n"
    "- 对所有结论给出关键数字与简要解释。\\n"
    "## 注意事项：\\n"
    "- 你只能通过提供的工具访问数据服务，禁止臆测或编造数据；\\n"
    "- 时间区间遵循 [start, end)；\\n"
    "- 指标计算需先取得真实值与预测值；\\n"
    "- 其他中间结果最好通过markdown表格展示。\\n"
)

# ---------------------------------------------------------------------------
# Conversation state & logging
# ---------------------------------------------------------------------------

_STORE: dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create chat history for a session."""
    if session_id not in _STORE:
        _STORE[session_id] = ChatMessageHistory()
    return _STORE[session_id]


def log_to_file(lines: List[str]) -> None:
    """Log conversation to a text file."""
    if not lines:
        return
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    log_dir = os.path.join(_HERE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line + "\\n")


# ---------------------------------------------------------------------------
# Agent builder
# ---------------------------------------------------------------------------


def build_agent(
    provider: str, model_name: str, temperature: float
) -> RunnableWithMessageHistory:
    """Build the agent with LLM and tools."""
    llm = get_llm(provider, model_name, temperature)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent_runnable = create_tool_calling_agent(llm, TOOLS, prompt)
    executor = AgentExecutor(
        agent=agent_runnable,
        tools=TOOLS,
        verbose=True,
        return_intermediate_steps=True,
    )

    return RunnableWithMessageHistory(
        executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="OD Agent CLI")
    parser.add_argument(
        "--provider",
        default="gemini",
        choices=["gemini", "qwen"],
        help="LLM 服务提供商",
    )

    parser.add_argument(
        "--model_name",
        default="gemini-2.5-flash-preview-05-20",
        help="LLM 模型名称 (Gemini: gemini-2.5-flash-preview-05-20, Qwen: qwen-plus 或 qwen-max)",
    )
    parser.add_argument("--temperature", type=float, default=0.6, help="采样温度")
    parser.add_argument("--base_url", type=str, default=None, help="后端服务地址")
    parser.add_argument(
        "--session", type=str, default="default-session", help="会话 ID"
    )
    args = parser.parse_args()

    # 设置默认模型名称
    if args.model_name is None:
        if args.provider == "gemini":
            args.model_name = "gemini-2.5-flash-preview-05-20"
        elif args.provider == "qwen":
            args.model_name = "qwen-turbo"

    if args.base_url:
        set_base_url(args.base_url)

    agent = build_agent(args.provider, args.model_name, args.temperature)
    logs: List[str] = []
    cfg = {"configurable": {"session_id": args.session}}

    try:
        while True:
            try:
                question = input("Q: ").strip()
            except EOFError:
                break
            if not question:
                break

            log_entry = [f"user: {question}", "-" * 40]
            error_occurred = False
            try:
                response = agent.invoke({"input": question}, config=cfg)
                content = response.get("output", str(response))
                log_entry.append(f"agent: {content}")
            except Exception as exc:
                error_occurred = True
                content = f"Agent 调用失败: {exc}"
                log_entry.append(f"agent_error: {content}")

            print("\\nA:", content, "\\n")

            log_entry.append("=" * 40)
            logs.extend(log_entry)

            if error_occurred:
                continue
    finally:
        log_to_file(logs)


if __name__ == "__main__":
    main()
