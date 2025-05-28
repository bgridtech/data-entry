from flask import Flask, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import threading
import os

app = Flask(__name__)
lock = threading.Lock()

# PostgreSQL DB connection (from environment variable)
def get_db_connection():
    url = urlparse(os.environ['DATABASE_URL'])
    return psycopg2.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname=url.path[1:],
        cursor_factory=RealDictCursor
    )

def generate_new_book_id(cursor):
    cursor.execute("SELECT book_id FROM books ORDER BY book_id ASC")
    rows = cursor.fetchall()

    existing_nums = sorted([int(row['book_id'][2:]) for row in rows if row['book_id'].startswith('BK')])

    expected = 1
    for num in existing_nums:
        if num == expected:
            expected += 1
        elif num > expected:
            break

    return f"BK{expected:04d}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_book():
    try:
        data = request.json
        name = data['name'].strip().upper()
        author = data['author'].strip().upper()
        shelf = data['shelf']
        cabinet = data['cabinet']
        confirm = data.get('confirm', False)

        with lock:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM books WHERE name = %s AND author = %s", (name, author))
            existing = cursor.fetchone()

            if existing:
                if not confirm:
                    return jsonify({
                        'status': 'duplicate',
                        'message': f"This book already exists with quantity {existing['qty']}. Add another copy?",
                        'book_id': existing['book_id']
                    })
                else:
                    cursor.execute("UPDATE books SET qty = qty + 1 WHERE id = %s", (existing['id'],))
                    conn.commit()
                    return jsonify({'status': 'success', 'book_id': existing['book_id'], 'qty': existing['qty'] + 1})
            else:
                book_id = generate_new_book_id(cursor)
                cursor.execute(
                    "INSERT INTO books (book_id, name, author, shelf, cabinet, qty) VALUES (%s, %s, %s, %s, %s, %s)",
                    (book_id, name, author, shelf, cabinet, 1)
                )
                conn.commit()
                return jsonify({'status': 'success', 'book_id': book_id, 'qty': 1})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(debug=True)
