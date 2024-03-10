# syntax=docker/dockerfile:1
FROM python:3.11.6-slim

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

WORKDIR /app

# Copy the source code into the container.
COPY fetch.py .
COPY test.sh .

CMD ["bash", "test.sh"]
