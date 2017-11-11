import sqlite3

conn = sqlite3.connect('database.db')


def get_data():
    with conn:
        results = conn.execute('select data, anger, disgust, fear, joy, sadness, surprise from texts')
        return [row for row in results]


if __name__ == '__main__':
    get_data()
    pass
