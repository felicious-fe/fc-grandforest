import redis
import rq
from flask import Blueprint, current_app, render_template, request
from fc_server.api import local_mean, next_step, redis_get, redis_set


r = redis.Redis(host='localhost', port=6379, db=0)
tasks = rq.Queue('fc_tasks', connection=r)
web_bp = Blueprint('web', __name__)
steps = ['setup', 'local_mean_calc', 'send_to_master', 'global_mean_calc', 'final']


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
            return f'master: {redis_get("master")}\ndata: {redis_get("data")}\nMean: {result}'
        else:
            return 'something is None weirdly'
    else:
        return 'Calculating results. Please wait...'


@web_bp.route('/params', methods=['GET'])
def params():
    """
    :return: current parameter values as a HTML page
    """
    master = redis_get('master')
    step = redis_get('step')
    local_data = redis_get('local_data')
    global_data = redis_get('global_data')
    data = redis_get('data')
    available = redis_get('available')
    return f"""
        master: {master}
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
        current_app.logger.info('[WEB] POST request to /run in step "start" -> wait setup not finished')
        return 'Wait until setup is done'
    elif cur_step == 'setup':
        current_app.logger.info('[WEB] POST request to /run in step "setup" -> read data')
        current_app.logger.info('[WEB] Upload file')
        if 'file' in request.files:
            file = request.files['file']
            file_data = file.read().decode("latin-1")
            data = list(map(int, file_data.strip().split(',')))
            current_app.logger.info(f'[WEB] data: {data}')
            redis_set('data', data)
            current_app.logger.info('[WEB] File successfully uploaded and processed')
            next_step()
            local_mean()
            return 'Calculating results. Please wait...'
        else:
            current_app.logger.info('[WEB] No File was uploaded')
            return 'Empty file...'
    elif cur_step == 'final':
        current_app.logger.info('[WEB] POST request to /run in step "final" -> GET request to "/"')
        # TODO weiterleitung zu route /
        return 'TODO'
    else:
        current_app.logger.info(f'[WEB] POST request to /run in step "{cur_step}" -> wait calculations not finished')
        return 'Calculating results. Please wait...'
