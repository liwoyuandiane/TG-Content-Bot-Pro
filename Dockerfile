FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache curl gcc musl-dev python3-dev && \
    pip install --no-cache-dir --upgrade pip && \
    adduser -D -s /bin/sh appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apk del --no-cache gcc musl-dev python3-dev 2>/dev/null || true

COPY main/ ./main/
COPY start.sh .

RUN chmod +x start.sh && mkdir -p /app/logs /app/sessions && chown -R appuser:appuser /app

USER appuser

EXPOSE 28089

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:28089/health || exit 1

CMD ["sh", "start.sh"]