import json
import time
import os
import pytz
from numpy import random
from datetime import datetime, timezone
from flask import Flask, render_template, url_for, request, session, redirect
from flask_socketio import SocketIO, emit
from threading import Lock
from models import db, User


def setup_app(app):
    @app.before_first_request
    def create_tables():
        db.create_all()

    db.init_app(app)

def create_app(config=None):
    app = Flask(__name__)
    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith('.py'):
            app.config.from_pyfile(config)
    setup_app(app)
    return app

app = create_app({
    'SECRET_KEY': 'secret',
    'OAUTH2_REFRESH_TOKEN_GENERATOR': True,
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///db.sqlite',
})

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None
thread = None
thread_lock = Lock()
socketio = SocketIO(app, async_mode=async_mode)


def generate_live_data():
    date = datetime.now(pytz.timezone('Europe/Berlin')).strftime("%Y-%m-%d %H:%M:%S%z")
    userConsumption = random.randint(0, 4000)
    groupConsumption = random.randint(0, 50000)
    selfSufficiency = random.randint(0, 101)
    user_icon = "testuser"
    user_name = "Harry Potter"
    user_level = random.randint(0, 100)
    group_icon = "testgroup"
    group_name = "Hogwarts"
    group_level = random.randint(0, 100)
    data = {
            "date": date,
            "userConsumption": userConsumption,
            "groupConsumption": groupConsumption,
            "selfSufficiency": selfSufficiency,
            "consumersUser": {
                              "icon": user_icon, 
                              "name": user_name, 
                              "level": user_level
                             },
            "consumersGroup": {
                               "icon": group_icon, 
                               "name": group_name, 
                               "level": group_level
                              }
           }
    return json.dumps(data)


def background_thread():
    """Example of how to send server generated events to clients.
    Emit live data every 10 seconds."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        live_data = generate_live_data()
        socketio.emit('my_response',
                      {'data': live_data, 'count': count},
                      namespace='/test')


def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None


@app.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if not user: 
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        session['id'] = user.id
        return redirect('/')
    user = current_user()
    return render_template('home.html', async_mode=socketio.async_mode,
                           user=user)


@app.route('/logout')
def logout():
    del session['id']
    return redirect('/')

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


if __name__ == '__main__':
    socketio.run(app, debug=True)
