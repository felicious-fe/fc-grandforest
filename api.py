import pickle
import rq
from flask import Blueprint, jsonify, request, current_app
import numpy as np

from redis import r, redis_get, redis_set

r.set('available', pickle.dumps(False))
r.set('step', pickle.dumps('start'))
r.set('step_id', pickle.dumps(0))
steps = ['setup', 'local_mean_calc', 'send_to_master', 'global_mean_calc', 'final']
r.set('local_data', pickle.dumps(True))
r.set('global_data', pickle.dumps(True))

api_bp = Blueprint('api', __name__)
tasks = rq.Queue('fc_tasks', connection=r)


@api_bp.route('/status', methods=['GET'])
def status():
    """
    GET request to /status, if True is returned a GET data request will be send
    :return: JSON with key 'available' and value True or False
    """
    current_app.logger.info('[API] /status GET request')
    available = redis_get('available')
    return jsonify({'available': True if available else False})


@api_bp.route('/data', methods=['GET', 'POST'])
def data():
    """
    GET request to /data sends data to global server
    POST request to /data pulls data from global server
    :return: GET request: JSON with key 'data' and value data
             POST request: JSON True
    """
    # data will only be sent by the slave in the step send_to_master
    current_app.logger.info(f'[API] /data {r.get("step")}')
    current_app.logger.info(f'[API] /data {pickle.loads(r.get("step"))}')

    # data will be pulled from flask object request in json format
    if request.method == 'POST':
        current_app.logger.info('[API] /data POST request')
        current_app.logger.info(request.get_json(True))
        global_data = redis_get('global_data')
        global_data.append(request.get_json(True)['data'])
        redis_set('global_data', global_data)
        global_mean()
        return jsonify(True)
    # data will be sent to the master
    elif request.method == 'GET':
        current_app.logger.info('[API] /data GET request')
        redis_set('available', False)
        data = redis_get('local_data')
        current_app.logger.info(data)
        return jsonify({'data': data})
    else:
        current_app.logger.info('[API] Wrong request type, only GET and POST allowed')
        return jsonify(True)


@api_bp.route('/setup', methods=['POST'])
def setup():
    """
    set setup params, id is the id of the client, master is True if the client is the master,
    in global_data the data from all clients (including the master) will be aggregated,
    clients is a list of all ids from all clients, nr_clients is the number of clients involved in the app
    :return: JSON True
    """
    current_app.logger.info('[API] SETUP')
    setup_params = request.get_json()
    current_app.logger.info(setup_params)
    redis_set('id', setup_params['id'])
    master = setup_params['master']
    redis_set('master', master)
    if master:
        redis_set('global_data', [])
    redis_set('clients', setup_params['clients'])
    redis_set('nr_clients', len(setup_params['clients']))
    next_step()
    current_app.logger.info('[API] Setup parameters saved')
    return jsonify(True)


def next_step():
    step_id = redis_get('step_id')

    redis_set('step', steps[step_id])
    redis_set('step_id', step_id+1)


def global_mean():
    """
    calculates the global mean if the data of all clients arrived
    """
    current_app.logger.info('[API] run global_mean')
    global_data = redis_get('global_data')
    nr_clients = redis_get('nr_clients')
    current_app.logger.info(f'[API] global data:{global_data}')
    current_app.logger.info(f'[API] nr_clients:{nr_clients}')
    if len(global_data) == nr_clients:
        next_step()
        current_app.logger.info('[API] All participants have sent their data')
        mean = 0
        number_samples = 1
        sum = 0
        counter = 0

        for i in global_data:
            sum += i[mean]*i[number_samples]
            counter += i[number_samples]

        result = str(sum/counter)
        current_app.logger.info(f'[API] global mean result: {result}')
        redis_set('result', result)
        next_step()
    else:
        current_app.logger.info('[API] The coordinator has not received data from all clients yet')


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
        client_id = redis_get('id')
        current_app.logger.info(f'[API] local mean of client {client_id}: {mean} with {nr_samples} samples')
        if redis_get('master'):
            next_step()
            global_data = redis_get('global_data')
            global_data.append((mean, nr_samples))
            redis_set('global_data', global_data)
            global_mean()
        else:
            redis_set('local_data', (mean, nr_samples))
            next_step()
            redis_set('available', True)
