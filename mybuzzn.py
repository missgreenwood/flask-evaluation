import json
import pytz
from numpy import random
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Lock

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


def generate_live_data():
    date = (datetime.utcnow().replace(tzinfo=pytz.utc)).strftime("%Y-%M-%d %H:%M:%S%z")
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


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': 'Connected', 'count': 0})


if __name__ == '__main__':
    socketio.run(app, debug=True)
