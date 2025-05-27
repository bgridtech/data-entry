from flask import Flask, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import threading

app = Flask(__name__)
lock = threading.Lock()

# Configure Supabase PostgreSQL DB connection
db_config = {
    'host': 'aws-0-ap-southeast-1.pooler.supabase.com',
    'port': 6543,
    'user': 'postgres.pzqjtrazhpzqcncfdavh',
    'password': 'gxkhgtckytchglutcgjgc',  # Replace with your actual password
    'dbname': 'postgres'
}

def get_db_connection():
    return psycopg2.connect(**db_config, cursor_factory=RealDictCursor)

def generate_new_book_id(cursor):
    cursor.execute("SELECT book_id FROM books ORDER BY book_id ASC")
    rows = cursor.fetchall()

    existing_nums = sorted([int(row['book_id'][2:]) for row in rows])

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
                    cursor.execute("UPDATE books SET qty = qty + 1 WHERE id = %s RETURNING qty, book_id", (existing['id'],))
                    updated = cursor.fetchone()
                    conn.commit()
                    return jsonify({'status': 'success', 'book_id': updated['book_id'], 'qty': updated['qty']})
            else:
                book_id = generate_new_book_id(cursor)
                cursor.execute(
                    "INSERT INTO books (book_id, name, author, qty) VALUES (%s, %s, %s, %s)",
                    (book_id, name, author, 1)
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
