FROM python:3.11-slim

WORKDIR /app

RUN apt update && apt upgrade -y

COPY requirements.in requirements.in

RUN pip install pip-tools && \
    pip-compile requirements.in && \
    pip-sync
 
COPY . /app/

RUN pip install .

CMD PYTHONPATH=/app \
    kopf \
    run \
    --standalone \
    --liveness=http://0.0.0.0:8080/healthz \
    -A \
    -m orchestrator_operator.main