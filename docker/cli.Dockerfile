FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /cli

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY cli /cli

RUN python -m pip install --upgrade pip \
    && python -m pip install .

CMD ["zema", "--help"]
