from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from datetime import datetime
from typing import Optional
import uvicorn

#http://localhost:8000/docs

app = FastAPI()

# Подключение к базе данных PostgreSQL
db = psycopg2.connect(
    dbname="site",
    user="postgres",
    password="11111",
    host="localhost"
)

# Middleware для обработки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Модель для данных пользователя
class User(BaseModel):
    username: str
    password: str
    name: Optional [str] = None
    birth_date: Optional [datetime] = None


# Роут для регистрации пользователя
@app.post('/register')
def register(user: User):
    cursor = db.cursor()

    # Проверяем, что пользователь с таким именем еще не существует
    cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail='Username already exists')

    # Добавляем пользователя в базу данных
    cursor.execute("INSERT INTO users (username, password, name, birth_date) VALUES (%s, %s, %s, %s)", (user.username, user.password, user.name, user.birth_date))
    db.commit()

    cursor.close()

    return {'message': 'User registered successfully'}


# Роут для входа пользователя
@app.post('/login')
def login(user: User):
    cursor = db.cursor()

    # Отладочные выводы
    print("Username:", user.username)
    print("Password:", user.password)

    # Проверяем, что пользователь существует и пароль совпадает
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (user.username, user.password))
    result = cursor.fetchone()
    print("Result:", result)  # Отладочный вывод

    if result:
        info = get_user_info(user.username)
        info['message'] = 'Login successful'
        return info

    cursor.close()

    # Если пользователь не найден или пароль не совпадает, возвращаем ошибку
    raise HTTPException(status_code=401, detail='Invalid username or password')

# Роут для получения информации о пользователе по его почте
@app.get('/user_info/{email}')
def get_user_info(email: str):
    cursor = db.cursor()

    # Проверяем, что пользователь с таким адресом электронной почты существует
    cursor.execute("SELECT * FROM users WHERE username = %s", (email,))
    user = cursor.fetchone()

    cursor.close()

    if user:
        print(user)
        # Возвращаем информацию о пользователе
        return {
            'username': user[1],
            'name': user[3],
            'birth_date': user[4],
            'user_id': user[0]

        }
    else:
        # Если пользователь не найден, возвращаем ошибку
        raise HTTPException(status_code=404, detail='User not found')


# Роут для записи на курс или переноса даты, если запись уже существует
@app.post('/enroll_course/{user_id}/{course_id}/{date}')
def enroll_course(user_id: int, course_id: int, date: datetime):
    cursor = db.cursor()

    # Проверяем, существует ли уже запись на курс для данного пользователя и курса
    cursor.execute("SELECT * FROM course_enrollments WHERE is_active is TRUE and user_id = %s AND course_id = %s", (user_id, course_id))
    enrollment = cursor.fetchone()

    if enrollment:
        # Если запись уже существует, обновляем дату записи
        cursor.execute("UPDATE course_enrollments SET enrollment_date = %s WHERE user_id = %s AND course_id = %s", (date, user_id, course_id))
    else:
        # Если запись не существует, создаем новую запись на курс
        cursor.execute("INSERT INTO course_enrollments (user_id, course_id, enrollment_date) VALUES (%s, %s, %s)", (user_id, course_id, date))

    db.commit()
    cursor.close()

    return {'message': 'Course enrollment successful'}

# Роут для отмены записи на курс
@app.put('/cancel_enrollment/{enrollment_id}')
def cancel_enrollment(enrollment_id: int):
    cursor = db.cursor()



    # Отменяем запись на курс путем установки флага is_active в False
    cursor.execute("UPDATE course_enrollments SET is_active = FALSE WHERE id = %s", (enrollment_id,))
    db.commit()
    cursor.close()

    return {'message': 'Enrollment canceled successfully'}

# Роут для получения текущих записей на курсы для определенного пользователя
@app.get('/current_enrollments/{user_id}')
def current_enrollments(user_id: int):
    cursor = db.cursor()

    # Получаем текущие записи на курсы для определенного пользователя, учитывая только активные записи
    cursor.execute("SELECT ce.id, c.course_name, ce.enrollment_date FROM course_enrollments ce JOIN courses c ON ce.course_id = c.id WHERE ce.user_id = %s AND ce.is_active = TRUE", (user_id,))
    enrollments = cursor.fetchall()

    cursor.close()

    # Форматируем данные перед отправкой
    formatted_enrollments = [{'id': row[0], 'course_name': row[1], 'enrollment_date': row[2]} for row in enrollments]
    return formatted_enrollments



# Добавим запуск сервера приложения при запуске файла main.py
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
