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
            chat_data = {
                "session_id": session_id,
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

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有会话列表

        Returns:
            会话信息列表
        """
        sessions = []
        try:
            for file_path in self.storage_dir.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    chat_data = json.load(f)
                    sessions.append(
                        {
                            "session_id": chat_data.get("session_id", file_path.stem),
                            "created_at": chat_data.get("created_at", ""),
                            "updated_at": chat_data.get("updated_at", ""),
                            "message_count": len(chat_data.get("messages", [])),
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
