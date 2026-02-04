# Pythonning eng yengil versiyasini tanlaymiz
FROM python:3.10-slim

# Ishchi katalogni yaratamiz
WORKDIR /app

# Barcha fayllarni nusxalaymiz
COPY . .

# Kutubxonalarni o'rnatamiz
RUN pip install --no-cache-dir -r requirements.txt

# Botni ishga tushiramiz
CMD ["python", "main.py"]
