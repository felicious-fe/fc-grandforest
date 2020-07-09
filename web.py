import rq
from flask import Blueprint, current_app, render_template, request
import numpy as np

from redis_util import redis_get, r, redis_set

tasks = rq.Queue('fc_tasks', connection=r)
web_bp = Blueprint('web', __name__)
steps = ['setup', 'local_mean_calc', 'send_to_coordinator', 'global_mean_calc', 'final']


@web_bp.route('/', methods=['GET'])
def root():
    """
    decides which HTML page content will be shown to the user
    :return: step == 'start': the setup is not yet finished and the program cannot start yet
             step == 'setup': user can define parameters and upload data
             step == 'final': the results of the global mean will be shown
             else: the calculations are not yet finished
    """
    step = redis_get('step')
    if step == 'start':
        return 'Please wait until setup is done!'
    elif step == 'setup':
        current_app.logger.info('[WEB] Before rendering start_client.html')
        return render_template('start_client.html')
    elif step == 'final':
        result = redis_get('result')
        if result is not None:
            return f'coordinator: {redis_get("coordinator")}\ndata: {redis_get("data")}\nMean: {result}'
        else:
            return 'something is None weirdly'
    else:
        return 'Calculating results. Please wait...'


@web_bp.route('/params', methods=['GET'])
def params():
    """
    :return: current parameter values as a HTML page
    """
    coordinator = redis_get('coordinator')
    step = redis_get('step')
    local_data = redis_get('local_data')
    global_data = redis_get('global_data')
    data = redis_get('data')
    available = redis_get('available')
    return f"""
        coordinator: {coordinator}
        step: {step}
        local data: {local_data}
        global data: {global_data}
        data: {data}
        available: {available}
        """


@web_bp.route('/run', methods=['POST'])
def run():
    """
    POST request to /run with the data as a file
    step == 'setup': the file will be read
    step == 'final': calculations are done, a GET request to '/' will be send
    else: a message for the relevant step will be shown
    :return: HTML page with content to the relevant step
    """
    cur_step = redis_get('step')
    if cur_step == 'start':
        return 'Wait until setup is done'
    elif cur_step == 'setup':
        if 'file' in request.files:
            file = request.files['file']
            file_data = file.read().decode("latin-1")
            redis_set('data', list(map(int, file_data.strip().split(','))))
            local_mean()
            return 'Calculating results. Please wait...'
        else:
            return 'Empty file...'
    elif cur_step == 'final':
        return 'Go to the front page'
    else:
        return 'Calculating results. Please wait...'


def local_mean():
    """
    :return: the mean of the local array and the length of the local array as a tuple
    """
    current_app.logger.info('[API] run local_mean')
    local_data = redis_get('data')
    if local_data is None:
        current_app.logger.info('[API] Data is None')
        return None
    else:
        mean = np.mean(local_data)
        nr_samples = len(local_data)
        if redis_get('coordinator'):
            global_data = redis_get('global_data')
            global_data.append((mean, nr_samples))
            redis_set('global_data', global_data)
        else:
            redis_set('local_data', (mean, nr_samples))
            redis_set('available', True)
