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
# ... (تمام اسٹیجز ویسے ہی رہیں گے) ...

# ایپلیکیشن چلانے کا حکم (پرانی حالت میں واپس)
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:8000"]

