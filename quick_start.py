#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @File Name:     quick_start
# @Author :       Jun
# @Date:          2024/12/19
# @Description :  OD-Agent 项目快速启动脚本

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path


class Colors:
    """终端颜色输出"""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_colored(message, color=Colors.WHITE):
    """打印彩色消息"""
    print(f"{color}{message}{Colors.END}")


def check_python_version():
    """检查Python版本"""
    print_colored("🐍 检查Python版本...", Colors.CYAN)
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_colored("❌ 需要Python 3.8或更高版本", Colors.RED)
        return False
    print_colored(
        f"✅ Python版本: {version.major}.{version.minor}.{version.micro}", Colors.GREEN
    )
    return True


def install_requirements(requirements_file, service_name):
    """安装依赖包"""
    if not os.path.exists(requirements_file):
        print_colored(f"⚠️  未找到依赖文件: {requirements_file}", Colors.YELLOW)
        return True

    print_colored(f"📦 安装 {service_name} 依赖...", Colors.CYAN)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            capture_output=True,
            text=True,
            check=True,
        )
        print_colored(f"✅ {service_name} 依赖安装成功", Colors.GREEN)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ {service_name} 依赖安装失败: {e.stderr}", Colors.RED)
        return False


def start_backend():
    """启动后端服务"""
    print_colored("🚀 启动后端服务...", Colors.CYAN)
    backend_dir = Path("agent/backend")
    os.chdir(backend_dir)

    try:
        # 启动FastAPI服务
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8502",
                "--reload",
            ]
        )
        print_colored("✅ 后端服务启动成功 (端口: 8502)", Colors.GREEN)
        return process
    except Exception as e:
        print_colored(f"❌ 后端服务启动失败: {e}", Colors.RED)
        return None


def start_agent():
    """启动Agent服务"""
    print_colored("🤖 启动Agent服务...", Colors.CYAN)
    agent_dir = Path("agent/agent")
    os.chdir(agent_dir)

    try:
        # 启动Agent服务
        process = subprocess.Popen([sys.executable, "agent_service.py"])
        print_colored("✅ Agent服务启动成功 (端口: 8503)", Colors.GREEN)
        return process
    except Exception as e:
        print_colored(f"❌ Agent服务启动失败: {e}", Colors.RED)
        return None


def start_frontend():
    """启动前端服务"""
    print_colored("🎨 启动前端服务...", Colors.CYAN)
    frontend_dir = Path("frontend")
    os.chdir(frontend_dir)

    try:
        # 启动Streamlit服务
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.port",
                "8501",
                "--server.address",
                "0.0.0.0",
            ]
        )
        print_colored("✅ 前端服务启动成功 (端口: 8501)", Colors.GREEN)
        return process
    except Exception as e:
        print_colored(f"❌ 前端服务启动失败: {e}", Colors.RED)
        return None


def wait_for_service(port, service_name, timeout=30):
    """等待服务启动"""
    import socket

    print_colored(f"⏳ 等待 {service_name} 启动...", Colors.YELLOW)
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:
                print_colored(f"✅ {service_name} 已就绪", Colors.GREEN)
                return True
        except:
            pass

        time.sleep(1)

    print_colored(f"⚠️  {service_name} 启动超时", Colors.YELLOW)
    return False


def main():
    """主函数"""
    print_colored("=" * 60, Colors.BOLD)
    print_colored("🚀 OD-Agent 项目快速启动", Colors.BOLD)
    print_colored("=" * 60, Colors.BOLD)

    # 检查Python版本
    if not check_python_version():
        return

    # 保存原始工作目录
    original_dir = os.getcwd()
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)

    processes = []

    try:
        # 安装依赖
        print_colored("\n📦 安装项目依赖...", Colors.CYAN)

        # 安装后端依赖
        if not install_requirements("agent/backend/requirements.txt", "后端"):
            return

        # 安装Agent依赖
        if not install_requirements("agent/agent/requirements.txt", "Agent"):
            return

        # 安装前端依赖
        if not install_requirements("frontend/requirements.txt", "前端"):
            return

        print_colored("\n🚀 启动所有服务...", Colors.CYAN)

        # 启动后端服务
        os.chdir(project_root)
        backend_process = start_backend()
        if backend_process:
            processes.append(("后端服务", backend_process))
            wait_for_service(8502, "后端服务")

        # 启动Agent服务
        os.chdir(project_root)
        agent_process = start_agent()
        if agent_process:
            processes.append(("Agent服务", agent_process))
            wait_for_service(8503, "Agent服务")

        # 启动前端服务
        os.chdir(project_root)
        frontend_process = start_frontend()
        if frontend_process:
            processes.append(("前端服务", frontend_process))
            wait_for_service(8501, "前端服务")

        # 显示访问信息
        print_colored("\n" + "=" * 60, Colors.BOLD)
        print_colored("🎉 所有服务启动完成！", Colors.GREEN)
        print_colored("=" * 60, Colors.BOLD)
        print_colored("📱 前端界面: http://localhost:8501", Colors.CYAN)
        print_colored("🔧 后端API: http://localhost:8502", Colors.CYAN)
        print_colored("🤖 Agent服务: http://localhost:8503", Colors.CYAN)
        print_colored("\n💡 按 Ctrl+C 停止所有服务", Colors.YELLOW)
        print_colored("=" * 60, Colors.BOLD)

        # 等待用户中断
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print_colored("\n🛑 正在停止所有服务...", Colors.YELLOW)

    except Exception as e:
        print_colored(f"❌ 启动过程中出现错误: {e}", Colors.RED)

    finally:
        # 清理所有进程
        print_colored("🧹 清理进程...", Colors.CYAN)
        for name, process in processes:
            try:
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                    print_colored(f"✅ {name} 已停止", Colors.GREEN)
            except:
                try:
                    process.kill()
                except:
                    pass

        # 恢复原始工作目录
        os.chdir(original_dir)
        print_colored("👋 所有服务已停止，再见！", Colors.GREEN)


if __name__ == "__main__":
    main()
