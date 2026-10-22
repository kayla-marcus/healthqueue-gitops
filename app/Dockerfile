# ---- Stage 1: builder ----
# Compiles main.py to bytecode. Nothing from this stage ships except the result.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY main.py .
RUN python -m compileall -b main.py

# ---- Stage 2: final image ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Fixed numeric IDs so Kubernetes can verify the container is not root
RUN groupadd --gid 10001 appuser && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY --from=builder /build/main.pyc .

USER 10001
EXPOSE 8000

# Used by plain Docker only; Kubernetes uses its own probes (see k8s/deployment.yaml)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["python", "main.pyc"]
