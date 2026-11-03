FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY bot.py assistant.py store.py policy.json seed_orders.json ./

CMD ["python", "bot.py"]
