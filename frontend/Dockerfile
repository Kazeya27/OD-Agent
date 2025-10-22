FROM python:3.12-slim
LABEL authors="Jun"

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple

CMD ["streamlit", "run", "app.py"]