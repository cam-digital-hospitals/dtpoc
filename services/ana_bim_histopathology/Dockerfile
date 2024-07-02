FROM --platform=linux/amd64 python:3.12-slim

RUN apt-get update && \
    apt-get upgrade --yes && \
    apt-get install --yes gcc && \
    rm -rf /var/lib/apt/lists/* && \
    pip install pip-tools

WORKDIR /app

# Copy the requirements file and compile it
COPY requirements.in /app/
RUN pip-compile requirements.in && \
    pip-sync

COPY src /app/

WORKDIR /

CMD python -m app