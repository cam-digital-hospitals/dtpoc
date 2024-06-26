FROM python:3.11-slim

WORKDIR /app

RUN apt update && apt upgrade -y

COPY requirements.in requirements.in

RUN pip install pip-tools && \
    pip-compile requirements.in && \
    pip-sync

COPY ./src/* /app/

CMD PYTHONPATH=/app \
    python main.py