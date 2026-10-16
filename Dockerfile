FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

RUN addgroup --system --gid 10001 taskflow \
    && adduser --system --uid 10001 --ingroup taskflow taskflow \
    && chown -R taskflow:taskflow /code

USER taskflow

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
