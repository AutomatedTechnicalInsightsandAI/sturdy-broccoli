import sqlite3

class SafeDatabase:
    def __init__(self, db_name):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()

    def insert_content(self, content):
        try:
            self.cursor.execute('''
                INSERT INTO content_table (content)
                VALUES (?)
            ''', (content,))
            self.connection.commit()
        except sqlite3.Error as e:
            print(f'Error inserting content: {e}')
            self.connection.rollback()  # Rollback in case of error
        finally:
            self.close()

    def close(self):
        self.connection.close()

# Example usage
if __name__ == '__main__':
    db = SafeDatabase('content.db')
    db.insert_content('Sample content for safe insertion.')
