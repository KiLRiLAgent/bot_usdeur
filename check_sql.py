import sqlite3

def view_users():
    conn = sqlite3.connect('chat_bot_usd/users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()

    for row in rows:
        print(row)

    conn.close()

# вызовите функцию, чтобы просмотреть данные
view_users()
