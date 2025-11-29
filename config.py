import os

# Бот попытается найти токен в настройках Railway
# Если не найдет (например, при запуске на компьютере), возьмет тот, что в кавычках
BOT_TOKEN = os.getenv("BOT_TOKEN", "8447886275:AAF8tN0O1IWV_jPWbjc5ILIbXuHRMSIwHFQ")

# То же самое для ID админа
raw_admin_id = os.getenv("ADMIN_ID", "7903041939")
ADMIN_ID = int(raw_admin_id)