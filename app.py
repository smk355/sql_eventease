from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ishu@0708",
    database="EventEaseDB"
)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            return redirect(url_for('home'))
        return render_template('login.html', message="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            return render_template('register.html', message="Email already registered")

        cursor.execute("INSERT INTO users (email, password, user_type) VALUES (%s, %s, %s)",
                     (email, password, user_type))
        db.commit()
        cursor.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Home route
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    if session['user_type'] == 'student':
        cursor.execute("""
            SELECT id, title, description, DATE_FORMAT(date, '%d-%m-%Y') as date, 
            TIME_FORMAT(event_time, '%h:%i %p') as event_time,
            location, category
            FROM events WHERE date >= CURDATE()
            ORDER BY date, event_time
        """)
    elif session['user_type'] == 'club':
        cursor.execute("""
            SELECT id, title, description, DATE_FORMAT(date, '%d-%m-%Y') as date,
            TIME_FORMAT(event_time, '%h:%i %p') as event_time,
            location, category
            FROM events WHERE created_by = %s
            ORDER BY date, event_time
        """, (session['user_id'],))
    
    events = cursor.fetchall()
    cursor.close()
    return render_template('event.html', events=events)

# Event details route with delete functionality
@app.route('/event/<int:event_id>', methods=['GET', 'POST', 'DELETE'])
def event_details(event_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, title, description, DATE_FORMAT(date, '%d-%m-%Y') as date,
        TIME_FORMAT(event_time, '%h:%i %p') as event_time,
        location, category, created_by, created_at
        FROM events WHERE id = %s
    """, (event_id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        return "Event not found", 404
    
    if request.method == 'DELETE' and session['user_type'] == 'club':
        if event['created_by'] != session['user_id']:
            cursor.close()
            return "Unauthorized", 403
        
        cursor.execute("DELETE FROM rsvp WHERE event_id = %s", (event_id,))
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        db.commit()
        cursor.close()
        return jsonify({"message": "Event deleted successfully"}), 200
    
    if session['user_type'] == 'student':
        if request.method == 'POST':
            cursor.execute("""
                INSERT INTO rsvp (event_id, student_id, name, email, mobile, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (event_id, session['user_id'], 
                 request.form['name'], request.form['email'],
                 request.form['mobile'], datetime.now()))
            db.commit()
            cursor.close()
            return render_template('event_details.html', event=event, message="RSVP successful!")
        cursor.close()
        return render_template('event_details.html', event=event)
    else:
        cursor.execute("""
            SELECT rsvp.*, users.email 
            FROM rsvp 
            JOIN users ON rsvp.student_id = users.id 
            WHERE event_id = %s
        """, (event_id,))
        participants = cursor.fetchall()
        cursor.close()
        return render_template('event_participants.html', event=event, participants=participants)

# Create new event
@app.route('/create_events', methods=['GET', 'POST'])
def create_events():
    if 'user_id' not in session or session['user_type'] != 'club':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        time = request.form.get('time')
        location = request.form.get('location')
        category = request.form.get('category')
        
        # Insert into database
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """INSERT INTO events (title, description, date, event_time, location, category, created_by, created_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""", 
            (title, description, date, time, location, category, session['user_id'])
        )
        db.commit()
        cursor.close()
        
        return redirect(url_for('home'))
        
    return render_template('create_events.html')

if __name__ == '__main__':
    app.run(debug=True)