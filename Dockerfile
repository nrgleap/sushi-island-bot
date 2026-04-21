FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "bot.py"]
