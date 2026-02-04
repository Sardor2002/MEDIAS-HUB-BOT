# Pythonning eng yengil va barqaror versiyasini tanlaymiz
FROM python:3.10-slim

# Ishchi katalogni belgilaymiz
WORKDIR /app

# Kutubxonalar ro'yxatini nusxalaymiz
COPY requirements.txt .

# Kutubxonalarni o'rnatamiz (keshlarsiz, joyni tejash uchun)
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni nusxalaymiz
COPY . .

# Botni ishga tushirish buyrug'i
CMD ["python", "main.py"]