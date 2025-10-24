# -*- coding: utf-8 -*-
# @File Name:     chat_storage
# @Author :       Jun
# @Date:          2024/12/19
# @Description :  聊天记录存储模块

import json
import os
import datetime
from typing import List, Dict, Any
from pathlib import Path


class ChatStorage:
    """聊天记录存储类"""

    def __init__(self, storage_dir: str = "chat_history"):
        """
        初始化聊天存储

        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.storage_dir / f"{session_id}.json"

    def save_chat(self, session_id: str, messages: List[Dict[str, Any]]) -> bool:
        """
        保存聊天记录

        Args:
            session_id: 会话ID
            messages: 消息列表

        Returns:
            是否保存成功
        """
        try:
            session_file = self._get_session_file(session_id)

            # 检查是否有用户消息，如果有则更新会话名称为时间格式
            has_user_messages = any(msg.get("role") == "user" for msg in messages)
            if has_user_messages:
                # 获取第一个用户消息的时间作为会话名称
                user_messages = [msg for msg in messages if msg.get("role") == "user"]
                if user_messages:
                    try:
                        # 尝试从消息中获取时间，如果没有则使用当前时间
                        first_user_time = datetime.datetime.now()
                        session_name = (
                            f"对话_{first_user_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    except:
                        session_name = f"对话_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    session_name = (
                        f"对话_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
            else:
                # 如果没有用户消息，保持原有名称或使用默认名称
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        session_name = existing_data.get(
                            "session_name",
                            f"对话_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        )
                except:
                    session_name = (
                        f"对话_{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )

            chat_data = {
                "session_id": session_id,
                "session_name": session_name,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "messages": messages,
            }

            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存聊天记录失败: {e}")
            return False

    def load_chat(self, session_id: str) -> List[Dict[str, Any]]:
        """
        加载聊天记录

        Args:
            session_id: 会话ID

        Returns:
            消息列表
        """
        try:
            session_file = self._get_session_file(session_id)
            if not session_file.exists():
                return []

            with open(session_file, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
                return chat_data.get("messages", [])
        except Exception as e:
            print(f"加载聊天记录失败: {e}")
            return []

    def _has_actual_conversation(self, messages: List[Dict[str, Any]]) -> bool:
        """
        检查会话是否有实际的对话内容（用户消息）

        Args:
            messages: 消息列表

        Returns:
            是否有实际对话内容
        """
        if not messages:
            return False

        # 检查是否有用户消息
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        return len(user_messages) > 0

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有会话列表（只返回有实际对话内容的会话）

        Returns:
            会话信息列表
        """
        sessions = []
        try:
            for file_path in self.storage_dir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                    messages = chat_data.get("messages", [])

                    # 只包含有实际对话内容的会话
                    if self._has_actual_conversation(messages):
                        sessions.append(
                            {
                                "session_id": chat_data.get(
                                    "session_id", file_path.stem
                                ),
                                "session_name": chat_data.get(
                                    "session_name", f"对话_{file_path.stem}"
                                ),
                                "created_at": chat_data.get("created_at", ""),
                                "updated_at": chat_data.get("updated_at", ""),
                                "message_count": len(messages),
                            }
                        )
        except Exception as e:
            print(f"获取会话列表失败: {e}")

        # 按更新时间排序
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        try:
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                session_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False

    def clear_all_sessions(self) -> bool:
        """
        清空所有会话

        Returns:
            是否清空成功
        """
        try:
            for file_path in self.storage_dir.glob("*.json"):
                file_path.unlink()
            return True
        except Exception as e:
            print(f"清空所有会话失败: {e}")
            return False

    def create_new_session(self, session_name: str = None) -> str:
        """
        创建新的会话标签页

        Args:
            session_name: 会话名称，如果为None则自动生成

        Returns:
            新的会话ID
        """
        now = datetime.datetime.now()
        timestamp = int(now.timestamp())
        if session_name is None:
            session_name = f"对话_{now.strftime('%Y-%m-%d %H:%M:%S')}"

        session_id = f"tab_{timestamp}_{hash(session_name) % 10000}"

        # 创建初始会话数据
        initial_data = {
            "session_id": session_id,
            "session_name": session_name,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "messages": [
                {
                    "role": "ai",
                    "content": "我是跨区域人员流动量预测助手，可以帮助您分析出行流量、预测拥堵情况、解释模型结果。",
                }
            ],
        }

        try:
            session_file = self._get_session_file(session_id)
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
            return session_id
        except Exception as e:
            print(f"创建新会话失败: {e}")
            return None

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典
        """
        try:
            session_file = self._get_session_file(session_id)
            if not session_file.exists():
                return None

            with open(session_file, "r", encoding="utf-8") as f:
                chat_data = json.load(f)
                return {
                    "session_id": chat_data.get("session_id", session_id),
                    "session_name": chat_data.get("session_name", f"对话_{session_id}"),
                    "created_at": chat_data.get("created_at", ""),
                    "updated_at": chat_data.get("updated_at", ""),
                    "message_count": len(chat_data.get("messages", [])),
                }
        except Exception as e:
            print(f"获取会话信息失败: {e}")
            return None

    def update_session_name(self, session_id: str, new_name: str) -> bool:
        """
        更新会话名称

        Args:
            session_id: 会话ID
            new_name: 新的会话名称

        Returns:
            是否更新成功
        """
        try:
            session_file = self._get_session_file(session_id)
            if not session_file.exists():
                return False

            with open(session_file, "r", encoding="utf-8") as f:
                chat_data = json.load(f)

            chat_data["session_name"] = new_name
            chat_data["updated_at"] = datetime.datetime.now().isoformat()

            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"更新会话名称失败: {e}")
            return False
