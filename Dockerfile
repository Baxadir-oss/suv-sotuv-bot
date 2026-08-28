# --- 1-bosqich: Mini App'ni (React) build qilish ---
FROM node:20-slim AS webapp-build
WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json* ./
RUN npm install
COPY webapp/ ./
RUN npm run build

# --- 2-bosqich: Python bot + Mini App API ---
FROM python:3.12-slim
WORKDIR /app

# SQLite uchun qo'shimcha paket kerak emas — aiosqlite toza Python.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/
COPY --from=webapp-build /webapp/dist ./webapp/dist

# Railway PORT o'zgaruvchisini avtomatik beradi
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "bot.main"]
