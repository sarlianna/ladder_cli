import sqlite3

DB_FILENAME = "ladder.db"

def init_db():
    print "initializing db..."
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE players
                 (name text PRIMARY KEY, elo real, wins int, losses int)''')
    conn.commit()

if __name__ == "__main__":
    init_db()
