FROM python:3.13-slim

WORKDIR /app

# Копируем только файл с зависимостями сначала
COPY requirements.txt .

# Устанавливаем зависимости с no-cache-dir и кэшируем этот слой
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код после установки зависимостей
COPY . .

CMD ["python", "main.py"]