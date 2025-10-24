## Развертывание проекта

```shell
python3 -m venv .venv
.venv\Scripts\activate.bat      # Для Windows
pip install -r requirements.txt
python3 manage.py runserver
```

## Примеры использования management command
```shell
# Создать данные с настройками по умолчанию (50 продуктов, 20 пользователей)
python manage.py seed

# Создать 100 продуктов и 30 пользователей
python manage.py seed --count=100 --users=30

# Создать только 20 продуктов
python manage.py seed --count=20
```

*Пароль для созданных пользователей:* `user_password`