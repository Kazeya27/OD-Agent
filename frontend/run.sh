#!/bin/bash

docker stop poc && docker rm poc

LOCAL_DIR=$(pwd)

docker run -d --name poc -p 8501:8501 \
  -v "$LOCAL_DIR":/app \
  poc:latest