import sqlite3

class Database:
    def __init__(self, db_name='users.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT DEFAULT NULL,
            last_name TEXT DEFAULT NULL,
            username TEXT DEFAULT NULL,
            language TEXT DEFAULT NULL,
            tokens INTEGER DEFAULT 0,
            chat BOOLEAN DEFAULT FALSE
        )
        ''')
        self.conn.commit()

    def log_user_data(self, user):
        c = 0
        if not self.is_user_logged(user.id):
            self.cursor.execute('''
            INSERT INTO users (id, first_name, last_name, username, language, tokens, chat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user.id, user.first_name,
                  user.last_name if user.last_name else None,
                  user.username if user.username else None,
                  user.language_code, 0, False))
            self.conn.commit()
            print(f"Користувач з ID {user.id} успішно доданий до бази.")
            c = 1
            
        else:
            print(f"Користувач з ID {user.id} вже існує в базі.")
            c = 0
        return c

    def is_user_logged(self, user_id):
        self.cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def get_user_tokens(self, user_id):
        self.cursor.execute('SELECT tokens FROM users WHERE id = ?', (user_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return 0

    def get_user_chat(self, user_id):
        self.cursor.execute('SELECT chat FROM users WHERE id = ?', (user_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        return 0

    def update_user_chat(self, user_id, new_status):
        if new_status in (0, 1):
            self.cursor.execute('UPDATE users SET chat = ? WHERE id = ?', (new_status, user_id))
            self.conn.commit()
        else:
            print("Помилка: новий статус чату повинен бути 0 або 1.")

    def update_user_tokens(self, user_id, new_balance):
        self.cursor.execute('UPDATE users SET tokens = ? WHERE id = ?', (new_balance, user_id))
        self.conn.commit()
        
    def get_all_users(self):
        self.cursor.execute('SELECT id, first_name, last_name, username, tokens FROM users')
        return self.cursor.fetchall()

    def close_db(self):
        self.conn.close()

if __name__ == "__main__":
    db = Database()
    db.close_db()
