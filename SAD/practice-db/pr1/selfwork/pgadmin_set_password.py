"""Пароль пользователя pgAdmin без проверки длины (setup.py update-user требует не меньше 6 символов,
а пароль методички — admin). Запуск внутри контейнера pgAdmin из каталога /pgadmin4:
  /venv/bin/python3 /tmp/pgadmin_set_password.py <email> <пароль>"""
import sys

sys.path.insert(0, '/pgadmin4')
import config  # noqa: E402
from flask_security.utils import hash_password  # noqa: E402
from pgadmin import create_app  # noqa: E402
from pgadmin.model import User, db  # noqa: E402

email, password = sys.argv[1:3]
app = create_app(config.APP_NAME + '-cli')
with app.test_request_context():
    user = User.query.filter_by(email=email).first()
    user.password = hash_password(password)
    db.session.commit()
print('pgAdmin: пароль пользователя', email, 'изменён')
