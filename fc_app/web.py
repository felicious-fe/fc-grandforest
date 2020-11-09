import redis
import rq
from flask import Blueprint, current_app
from fc_app.api import get_step, redis_get


r = redis.Redis(host='localhost', port=6379, db=0)
tasks = rq.Queue('fc_tasks', connection=r)
web_bp = Blueprint('web', __name__)
steps = ['setup', 'local_calculation', 'send_to_coordinator', 'global_calculation', 'share_results', 'final']


@web_bp.route('/', methods=['GET'])
def root():
    """
    decides which HTML page content will be shown to the user
    :return: step == 'start': the setup is not yet finished and the program cannot start yet
             step == 'setup': user can define parameters and upload data
             step == 'final': the results of the global mean will be shown
             else: the calculations are not yet finished
    """
    step = get_step()
    if step == 'start':
        current_app.logger.info('[WEB] Initializing')
        return 'Initializing'
    elif step == 'setup':
        current_app.logger.info('[WEB] Setup')
        return 'Setup'
    elif step == 'local_calculation':
        current_app.logger.info('[WEB] Calculating local mean')
        return 'Calculating local mean...'
    elif step == 'send_to_coordinator':
        current_app.logger.info('[WEB] Send local results to coordinator')
        return 'Send local results to coordinator...'
    elif step == 'global_calculation':
        current_app.logger.info('[WEB] Aggregate local results and compute global mean')
        return 'Aggregate local results and compute global mean...'
    elif step == 'share_results':
        if not redis_get('coordinator'):
            current_app.logger.info('[WEB] Receiving global mean from coordinator')
            return 'Receiving global mean from coordinator...'
        else:
            current_app.logger.info('[WEB] Broadcasting global mean to other clients')
            return 'Broadcasting global mean to other clients'
    elif step == 'final':
        result = redis_get('result')
        if result is not None:
            return f'coordinator: {redis_get("is_coordinator")}\ndata: {redis_get("data")}\nMean: {result}'
        else:
            return 'something is None weirdly'
    else:
        return 'Calculating results. Please wait...'


@web_bp.route('/params', methods=['GET'])
def params():
    """
    :return: current parameter values as a HTML page
    """
    is_coordinator = redis_get('is_coordinator')
    step = redis_get('step')
    local_data = redis_get('local_data')
    global_data = redis_get('global_data')
    data = redis_get('data')
    available = redis_get('available')
    return f"""
        is_coordinator: {is_coordinator}
        step: {step}
        local data: {local_data}
        global data: {global_data}
        data: {data}
        available: {available}
        """
