FROM python:3.11-slim


# 设置 pip 镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# # 设置 apt 镜像源（以 Ubuntu/Debian 为例）
# RUN sed -i 's@http://deb.debian.org@https://mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
#     sed -i 's@http://security.debian.org@https://mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
#     apt-get update && apt-get install -y --no-install-recommends \
#     build-essential

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# RUN apt-get update && apt-get install -y \
#     gcc \
#     g++ \
#     && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/dumps/traces

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]