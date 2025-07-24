# filename: Dockerfile
# --- اسٹیج 1: بلڈر (Builder) ---
FROM python:3.11-slim as builder
WORKDIR /opt/venv
RUN python -m venv .
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- اسٹیج 2: فائنل امیج (Final Image) ---
FROM python:3.11-slim
WORKDIR /app
RUN addgroup --system nonroot && adduser --system --ingroup nonroot nonroot
USER nonroot
COPY --from=builder /opt/venv /opt/venv
COPY . .
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8000
# اپ ڈیٹ شدہ کمانڈ
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
