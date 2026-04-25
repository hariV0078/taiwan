import sqlite3

def alter_db():
    conn = sqlite3.connect('circularx.db')
    try:
        conn.execute('ALTER TABLE user ADD COLUMN trust_score FLOAT DEFAULT 1.0')
        print("Added trust_score to user table")
    except sqlite3.OperationalError as e:
        print(f"Skipping user table alter: {e}")
        
    try:
        conn.execute('ALTER TABLE "transaction" ADD COLUMN updated_at DATETIME')
        print("Added updated_at to transaction table")
    except sqlite3.OperationalError as e:
        print(f"Skipping transaction table alter: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_db()
