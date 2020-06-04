import pickle
import queue as q
import redis
import rq
from flask import Blueprint, jsonify, request, current_app
from lifelines.utils import (check_nans_or_infs,normalize,StepSizer,ConvergenceError,inv_normal_cdf)
import pandas as pd
from collections import OrderedDict
import numpy as np
from scipy.linalg import solve as spsolve, LinAlgError, norm
import json
from scipy import stats


pool = redis.BlockingConnectionPool(host='localhost', port=6379, db=0, queue_class=q.Queue)
r = redis.Redis(connection_pool=pool)

## PROCEDURE OF THE ALGORITHM
#steps = ['setup_master','send_to_slave','setup_slave', 'preprocessing','local_norm', 'send_to_master', 'global_norm', 'normalization','local_init','send_to_master','global_init','local_stat','send_to_master','update_beta','send_model_parameter','summary','send_to_slaves','final']

## INITIALIZATION OF SOME PARAMETER
r.set('available', pickle.dumps(False))
r.set('step', pickle.dumps('start'))
#r.set('step_id', pickle.dumps(0))

r.set('local_norm', pickle.dumps(True))
r.set('global_norm', pickle.dumps(True))

r.set('local_init', pickle.dumps(True))
r.set('global_init', pickle.dumps(True))

r.set('local_stat', pickle.dumps(True))
r.set('global_stat', pickle.dumps(True))

r.set('master_step',pickle.dumps('master_upload'))
r.set('slave_step',pickle.dumps('slave_upload'))

r.set('iteration',pickle.dumps(0))
r.set('converging',pickle.dumps(True))

api_bp = Blueprint('api', __name__)
tasks = rq.Queue('fc_tasks', connection=r)

CONVERGENCE_DOCS = "Please see the following tips in the lifelines documentation: https://lifelines.readthedocs.io/en/latest/Examples.html#problems-with-convergence-in-the-cox-proportional-hazard-model"


@api_bp.route('/status', methods=['GET'])
def status():
    """
    GET request to /status, if True is returned a GET data request will be send
    :return: JSON with key 'available' and value True (/data GET request) or False (/data POST request)

    """
    current_app.logger.info('[API] /status GET request')
    cur_step = redis_get( 'step' )
    available = redis_get('available')
    converging = redis_get('converging')

    current_app.logger.info(f'[API] step: {cur_step}')
    current_app.logger.info(f'[API] converging: {converging}')
    current_app.logger.info(f'[API] available: {available}')

    if cur_step=='normalization':
        # (slave and master: available = False)
        normalization()

    elif cur_step=='local_stat':
        # (slave and master: available = False)
        local_statistics_calculation()

    elif cur_step=='summary':
        # (slave and master: available = False)
        if redis_get('master'):
            redis_set('master_step','master_final')
            calculate_final_statistics()
        else:
            redis_set('slave_step','slave_final')

    return jsonify({'available': True if available else False})

@api_bp.route('/data', methods=['GET', 'POST'])
def data():
    """
    GET request to /data sends data
    POST request to /data pulls data
    :return: GET request: JSON with key 'data' and value data
             POST request: JSON True
    """

    master = redis_get('master')
    master_step = redis_get( 'master_step' )
    slave_step = redis_get( 'slave_step' )
    step = redis_get('step')

    current_app.logger.info('[API] /data request')

    current_app.logger.info(f'[API] step: {step}')

    # data will be pulled from flask object request as json format
    if request.method == 'POST':
        # print data which will be pulled
        current_app.logger.info( request.get_json( True ) )


        if master:
            # get local mean and standard deviation of slaves
            if master_step=='master_norm':
                current_app.logger.info( '[API] /data master_norm POST request ' )
                global_norm = redis_get('global_norm')
                data_append = request.get_json(True)['local_norm']
                mean_json = data_append[0]
                std_json = data_append[1]
                mean = pd.read_json(mean_json,typ='series',orient='records')
                std = pd.read_json(std_json,typ='series',orient='records')
                global_norm.append((mean,std))
                redis_set('global_norm', global_norm)
                global_normalization()
                return jsonify(True)

            # get initialized local statistics of slaves
            elif master_step=='master_init':
                current_app.logger.info( '[API] /data master_init POST request ' )
                global_init = redis_get( 'global_init' )
                data_append = request.get_json( True )[ 'local_init' ]
                zlr_json = data_append[ 0 ]
                distinct_times_json = data_append[ 1 ]
                count_d = data_append[2]
                zlr = pd.read_json(zlr_json, typ='series', orient='records' )
                distinct_times = pd.read_json( distinct_times_json, typ='series', orient='records' )
                global_init.append( (zlr,distinct_times,count_d ) )
                redis_set( 'global_init', global_init )
                #next_step() #global_init
                redis_set('step','global_init')
                redis_set( 'available', True ) # master will afterwards send the initial model parameter to the clients (GET)
                global_initialization()
                return jsonify( True )

            # get local aggregated statistics for each iteration of slaves
            elif master_step=='master_stat':
                current_app.logger.info( '[API] /data master_stat POST request ' )
                global_stat = redis_get('global_stat')
                data_append = request.get_json( True )[ 'local_stat' ]
                i1 = data_append[ 0 ]
                i2 = data_append[ 1 ]
                i3 = data_append[ 2 ]
                global_stat.append( (i1, i2, i3) )
                redis_set( 'global_stat', global_stat )
                redis_set( 'available',True ) # master will afterwards send the updated model parameter to the clients
                #next_step() # update beta
                redis_set('step','update_beta')
                global_beta_calculation()
                return jsonify( True )

        else:
            # get parameter of the cox model of master to display in the start_client.html
            if slave_step == 'slave_upload':
                current_app.logger.info( '[API] /data slave_upload POST request ' )
                upload_info = request.get_json( True )[ 'upload_info' ]
                max_steps = upload_info[0]
                precision = upload_info[1]
                duration_col = upload_info[2]
                event_col = upload_info[3]
                covariates_json = upload_info[4]
                covariates = json.loads(covariates_json)
                redis_set('max_steps',max_steps)
                redis_set('precision',precision)
                redis_set('duration_col',duration_col)
                redis_set('event_col',event_col)
                redis_set('covariates',covariates)
                redis_set('available',False)
                #next_step() # -> send to slave
                #next_step() # -> setup slave
                redis_set('step','setup_slave')
                return jsonify(True)

            # get global mean and standard deviation from master for further calculations
            elif slave_step == 'slave_norm':
                current_app.logger.info( '[API] /data slave_norm POST request ' )
                mean_std = request.get_json(True)['mean_std']
                mean_json = mean_std[ 0 ]
                std_json = mean_std[ 1 ]
                mean = pd.read_json( mean_json, typ='series', orient='records' )
                std = pd.read_json( std_json, typ='series', orient='records' )
                redis_set('global_mean',mean)
                redis_set('global_std',std)
                #next_step() #global_normalization
                #next_step() # normalization
                redis_set('step','normalization')
                return jsonify(True)

            # get initialized model parameter (zeros)
            elif slave_step == 'slave_init':
                current_app.logger.info( '[API] /data slave_init POST request ' )
                beta_0_json = request.get_json(True)['beta_0']
                beta_0 = json.loads(beta_0_json)
                redis_set('beta',beta_0)
                redis_set('step','local_stat')
                #next_step() # local_stat
                return jsonify(True)

            # get updated model parameter and converging criteria
            elif slave_step == 'slave_stat':
                current_app.logger.info( '[API] /data slave_stat POST request ' )
                data = request.get_json( True )[ 'beta' ]
                beta = json.loads( data[0] )
                converging = data[1]
                redis_set('converging',converging)
                redis_set( 'beta', beta)
                if converging:
                    #step_to_local_stat() #new iteration -> step: local_stat
                    redis_set('step','local_stat')
                    redis_set( 'available', False )
                else:
                    redis_set('step','summary')
                    redis_set('available',False) # slaves & master because no further data exchange
                return jsonify(True)

            # get result dataframe from master
            elif slave_step == 'slave_final':
                current_app.logger.info( '[API] /data slave_final POST request ' )
                result_json = request.get_json( True )[ 'result' ]
                result = pd.read_json(result_json,typ='frame',orient='records')
                redis_set('result',result)
                redis_set('step','final') # final.html will be displayed with summary dataframe
                return jsonify(True)

    # data will be send to the master
    elif request.method == 'GET':
        if master:
            # send parameter for cox regression to slaves
            if master_step == 'master_upload':
                current_app.logger.info( '[API] /data master_upload GET request ' )
                max_steps = redis_get('max_steps')
                precision = redis_get('precision')
                duration_col = redis_get('duration_col')
                event_col = redis_get('event_col')
                data = redis_get('data')
                covariates = data.columns.values
                index = np.argwhere( covariates == duration_col )
                covariates = np.delete(covariates,index)
                index = np.argwhere( covariates == event_col )
                covariates = np.delete(covariates,index)
                redis_set('covariates',covariates)
                covariates_json = covariates.tolist()
                covariates_json = json.dumps(covariates_json)
                redis_set('available',False)
                #next_step() # -> setup_slave
                #next_step() # -> preprocessing
                redis_set('step','preprocessing')
                redis_set( 'master_step', 'master_norm' )
                redis_set( 'slave_step', 'slave_norm' )
                preprocessing()
                return jsonify({'upload_info':(max_steps,precision,duration_col,event_col,covariates_json)})

            # send global mean and standard deviation to slaves
            elif master_step == 'master_norm':
                current_app.logger.info( '[API] /data master_norm GET request ' )
                global_mean = redis_get('global_mean')
                global_std = redis_get('global_std')
                mean_json = global_mean.to_json()
                std_json = global_std.to_json()
                redis_set('available',False)
                #next_step() #normalisation
                redis_set('step','normalization')
                return jsonify({'mean_std':(mean_json,std_json)})

            # send initial model parameter to slaves (zeros)
            elif master_step == 'master_init':
                # initial model parameter will be send to the clients, step_sizer and delta will also be initialized
                current_app.logger.info( '[API] /data master_init GET request ' )
                zr = redis_get( 'global_zr' )
                covariates = zr.axes[ 0 ]
                beta_0 = np.zeros((len(covariates),))
                beta_0_json = beta_0.tolist()
                beta_0_json = json.dumps(beta_0_json)
                redis_set('beta',beta_0)
                step_size = None
                step_sizer = StepSizer(step_size)
                step_size = step_sizer.next()
                redis_set('step_sizer',step_sizer)
                redis_set('step_size',step_size)

                delta = np.zeros_like(beta_0)
                redis_set('delta',delta)

                redis_set('available',False)
                #next_step() # local_stat
                redis_set('step','local_stat')
                return jsonify( {'beta_0': (beta_0_json)} )

            # send updated model parameter and convergence criteria to slaves
            elif master_step == 'master_stat':
                current_app.logger.info( '[API] /data master_stat GET request ' )
                beta = redis_get('beta')
                converging = redis_get('converging')
                beta_json = beta.tolist()
                beta_json = json.dumps( beta_json )
                redis_set( 'available', False ) # in /status local_statistics_calculation will be called
                if converging:
                    #step_to_local_stat() #new iteration -> step: local_stat
                    redis_set('step','local_stat')
                else:
                    redis_set('step','summary') # -> summary

                return jsonify({'beta':(beta_json,converging)})

            # send summary results to slaves
            elif master_step == 'master_final':
                current_app.logger.info( '[API] /data master_final GET request ' )
                result = redis_get('result')
                result_json = result.to_json()
                redis_set( 'available', False )
                redis_set('step','final')
                return jsonify({'result':(result_json)})

        else:
            # send local mean and standard deviation to master
            if slave_step == 'slave_norm':
                current_app.logger.info( '[API] /data slave_norm GET request ' )
                local_norm = redis_get('local_norm')
                current_app.logger.info(local_norm)
                mean = local_norm[0]
                std = local_norm[1]
                mean_json = mean.to_json()
                std_json = std.to_json()
                redis_set('available', False)
                return jsonify({'local_norm': (mean_json,std_json)})

            # send initial statistics to master
            elif slave_step=='slave_init':
                current_app.logger.info( '[API] /data slave_init GET request ' )
                local_init = redis_get('local_init')
                current_app.logger.info( local_init )
                zlr = local_init[0]
                distinct_times = local_init[1]
                numb_d_set = local_init[2]
                zlr_json = zlr.to_json()
                distinct_times_json = distinct_times.to_json()
                redis_set('available',False) # POST -> clients will get the initial model parameter
                #next_step() #global_init
                redis_set('step','global_init')
                return jsonify({'local_init':(zlr_json,distinct_times_json,numb_d_set)})

            # send updated aggregated statistics to master
            elif slave_step=='slave_stat':
                current_app.logger.info( '[API] /data slave_stat GET request ' )
                local_stat = redis_get('local_stat')
                current_app.logger.info(local_stat)
                i1 = local_stat[0]
                i2 = local_stat[1]
                i3 = local_stat[2]
                #next_step() # update beta
                #next_step() # send model parameter
                redis_set('step','send_model_parameter')
                redis_set( 'available', False )  # POST -> clients will get the new model parameter
                return jsonify( {'local_stat': (i1, i2, i3)} )

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
        redis_set('global_norm', [])
        redis_set('global_init',[])
        redis_set( 'global_stat', [])
    redis_set('clients', setup_params['clients'])
    redis_set('nr_clients', len(setup_params['clients']))

    #next_step() # -> setup_master
    redis_set('step','setup_master')
    current_app.logger.info('[API] Setup parameters saved')
    return jsonify(True)

#def next_step():
#    step_id = redis_get('step_id')
#    redis_set('step', steps[step_id])
#    redis_set('step_id', step_id+1)

#def step_to_local_stat():
#    step_id = redis_get( 'step_id' )
#    redis_set( 'step', 'local_stat')
#    redis_set( 'step_id', step_id - 3 ) # send_model_parameter -> update beta -> send_to_master -> local_stat

def redis_get(key):
    if key in r:
        return pickle.loads(r.get(key))
    else:
        return None

def redis_set(key, value):
    r.set(key, pickle.dumps(value))

def preprocessing():
    """
    Preprocesses the dataframe of the clients. Save X, T and E of the dataset.
    """
    current_app.logger.info('[API] run preprocessing')
    localdata = redis_get('data')
    duration_col = redis_get('duration_col')
    event_col = redis_get('event_col')

    if localdata is None:
        current_app.logger.info('[API] Data is None')
        return None
    elif duration_col is None:
        current_app.logger.info( '[API] Duration column is None')
        return None
    elif event_col is None:
        current_app.logger.info( '[API] Event column is None')
        return None
    else:
        sort_by = [duration_col, event_col] if event_col else [duration_col]
        data = localdata.sort_values(by=sort_by)
        T = data.pop(duration_col)
        E = data.pop(event_col)

        X = data.astype(float)
        T = T.astype(float)

        check_nans_or_infs(E)
        E = E.astype(bool)

        redis_set('X',X)
        redis_set('T',T)
        redis_set('E',E)

        current_app.logger.info( '[API] Preprocessing is done (X,T,E saved)' )

        #next_step() # local_norm
        redis_set('step','local_norm')
        local_normalization()

def local_normalization():
    """
    calculate mean and standard deviation of the local dataframe and send to the master

    """
    current_app.logger.info('[API] run local_normalization')
    X = redis_get('X')
    if X is None:
        current_app.logger.info('[API] X is None')
        return None
    else:
        norm_mean = X.mean(0)
        norm_std = X.std(0)
        client_id = redis_get('id')
        current_app.logger.info(f'[API] local_mean of client {client_id}: {norm_mean}')
        current_app.logger.info( f'[API] local_std of client {client_id}: {norm_std}' )
        if redis_get('master'):
            #next_step() # send_to_master
            redis_set('step','send_to_master')
            global_norm = redis_get('global_norm')
            global_norm.append((norm_mean, norm_std))
            redis_set('global_norm', global_norm)
            global_normalization()
        else:
            redis_set('local_norm', (norm_mean, norm_std))
            #next_step() # send_to_master
            redis_set('step','send_to_master')
            redis_set('available', True)

def global_normalization():
    """
    calculate the global mean and standard deviation if the data of all clients arrived
    """
    current_app.logger.info('[API] run global_normalization')
    global_norm = redis_get('global_norm')
    nr_clients = redis_get('nr_clients')
    if len(global_norm) == nr_clients:
        current_app.logger.info('[API] The data of all clients has arrived')
        mean = pd.Series()
        std = pd.Series()

        for client in global_norm:
            mean = mean.add(client[0],fill_value=0)
            std = std.add(client[1],fill_value=0)


        result_mean = mean/nr_clients
        result_std = std/nr_clients
        current_app.logger.info(f'[API] global mean result: {result_mean}')
        current_app.logger.info( f'[API] global standard deviation result: {result_std}' )
        redis_set('global_mean', result_mean)
        redis_set('global_std',result_std)
        redis_set( 'available', True )
        #next_step() # global_norm
        redis_set('step','global_norm')
    else:
        current_app.logger.info('[API] Not the data of all clients has been send to the master')

def normalization():
    """
    normalize dataset of client with global_mean and global_std
    """
    current_app.logger.info( '[API] run normalization of each client' )

    mean = redis_get('global_mean')
    std = redis_get('global_std')

    X = redis_get('X')
    X_norm = pd.DataFrame(normalize(X.values,mean.values,std.values),index=X.index,columns=X.columns)
    redis_set('X_norm',X_norm)
    current_app.logger.info( f'[API] normalized dataset: {X_norm}' )

    redis_set('master_step','master_init')
    redis_set('slave_step','slave_init')
    #next_step() # local_init
    redis_set('step','local_init')
    local_initialization()

def local_initialization():
    """
    calculate statistics D, zlr, and count_d of each client
    """
    current_app.logger.info( '[API] run local_initialization' )
    duration_col = redis_get('duration_col')
    event_col = redis_get('event_col')
    # sort dataframe by duration_column
    sort_by = [duration_col]
    data = redis_get('data')
    data = data.sort_values(by=sort_by)
    risk_set = {}
    death_set = {}
    numb_d_set = {}

    # get the distinct event times
    distinct_times = pd.Series(data[ duration_col ].unique() )

    for uniq_time in distinct_times:
        Ri = data[ data[ duration_col ] >= uniq_time ].index.tolist()
        Di = data[(data[ duration_col ] == uniq_time) & (data[ event_col ] == 1) ].index.tolist()
        risk_set[ uniq_time ] = Ri
        death_set[ uniq_time ] = Di
        numb_d_set[ str(uniq_time) ] = str(len( Di ))

    # calculate z-value (zlr) // sum over all distinct_times (sum of the covariates over all individuals in Di))
    zlr = pd.Series()
    X_norm = redis_get('X_norm')
    for time in distinct_times:
        covariates = X_norm.loc[ death_set[ time ], ]
        sum = covariates.sum( axis=0, skipna=True )
        zlr = zlr.add( sum, fill_value=0 )

    if redis_get( 'master' ):
        #next_step() # send_to_master
        redis_set('step','send_to_master')
        global_init = redis_get( 'global_init' )
        global_init.append( (zlr, distinct_times,numb_d_set) )
        redis_set( 'global_init', global_init )
        global_initialization()
    else:
        redis_set( 'local_init', (zlr, distinct_times,numb_d_set) )
        #next_step() # send_to_master
        redis_set('step','send_to_master')
        redis_set( 'available', True )

def global_initialization():
    """
    global initialization of the server: zlr, D, count_d

    """
    current_app.logger.info( '[API] run global_initialization' )
    global_init = redis_get( 'global_init' )
    nr_clients = redis_get( 'nr_clients' )
    if (len(global_init))==nr_clients:
        D = []
        zr = pd.Series()
        for client in global_init:
            zlr = client[0]
            distinct_times = client[1]
            D.extend(distinct_times.tolist())
            zr = zr.add(zlr, fill_value=0)

        # delete duplicates out of D to get the total number of distinct event times
        D = list( OrderedDict.fromkeys( D ) )
        D.sort()

        # sum over all sites |Dki| ({time i : |Dki|}
        count_d = {}
        for time in D:
            val = 0
            for client in global_init:
                n = client[2].get(str(time))
                if n is not None:
                    val = val + int(n)
            count_d[ time ] = val

        redis_set('global_count_d',count_d)
        redis_set('global_D',D)
        redis_set('global_zr',zr)
        current_app.logger.info( f'[API] global D: {D}' )
        current_app.logger.info( f'[API] global zr: {zr}' )
        current_app.logger.info( f'[API] global count_d: {count_d}' )

        redis_set( 'available', True ) # send beta_0 to slaves

    else:
        current_app.logger.info( '[API] Not the data of all clients has been send to the master' )

def local_statistics_calculation():

    """
    calculate three local aggregated statistics using the parameter beta.
    send them to the server.
    """

    current_app.logger.info( '[API] run local_statistics' )
    #test algorithm of lifelines
    i1 ={}
    i2 ={}
    i3 ={}

    X_norm = redis_get('X_norm')
    T = redis_get('T')
    beta = redis_get('beta')

    X = X_norm.values
    T = T.values

    n,d = X.shape
    risk_phi = 0
    risk_phi_x = np.zeros((d,))
    risk_phi_x_x = np.zeros((d,d))


    _, counts = np.unique(-T,return_counts=True)
    scores = np.exp(np.dot(X,beta))
    pos=n
    time_index=0
    for count_of_removal in counts:
        uniq_time = _[time_index]
        slice_ = slice(pos-count_of_removal,pos)
        X_at_t = X[slice_]

        phi_i = scores[slice_,None]
        phi_x_i = phi_i * X_at_t
        phi_x_x_i = np.dot(X_at_t.T,phi_x_i)

        risk_phi = risk_phi + phi_i.sum()
        risk_phi_x = risk_phi_x + (phi_x_i).sum(0)
        risk_phi_x_x = risk_phi_x_x + phi_x_x_i

        risk_phi_x_json = risk_phi_x.tolist()
        risk_phi_x_json = json.dumps( risk_phi_x_json )

        risk_phi_x_x_json = risk_phi_x_x.tolist()
        risk_phi_x_x_json = json.dumps( risk_phi_x_x_json )

        pos = pos-count_of_removal
        time = str(-uniq_time)
        i1[time] = risk_phi
        i2[time] = risk_phi_x_json
        i3[time] = risk_phi_x_x_json

        time_index+=1

    redis_set('master_step','master_stat')
    redis_set('slave_step','slave_stat')

    if redis_get( 'master' ):
        global_stat = redis_get( 'global_stat' )
        global_stat.append( (i1, i2,i3) )
        redis_set( 'global_stat', global_stat )
        redis_set('available',False) #POST -> master will get the aggregated statistics from slaves
        #next_step() # send_to_master
        redis_set('step','send_to_master')
        global_beta_calculation()
    else:
        redis_set( 'local_stat', (i1, i2,i3) )
        redis_set( 'available', True ) #GET -> slaves will send aggregated local statistics to master
        #next_step() #send_to_master
        redis_set( 'step', 'send_to_master' )

def global_beta_calculation():
    """
    Update the model parameter beta and hessian.
    """
    current_app.logger.info( '[API] run global_beta_calculation' )
    global_stat = redis_get( 'global_stat' )
    beta = redis_get('beta')
    nr_clients = redis_get( 'nr_clients' )

    converging = redis_get('converging')
    step_sizer = redis_get( 'step_sizer' )
    step_size = redis_get('step_size')
    delta = redis_get('delta')

    precision = redis_get('precision')
    max_steps = redis_get('max_steps')
    iteration = redis_get('iteration')

    if (len( global_stat )) == nr_clients:
        iteration = iteration + 1
        h,g = get_efron_values(global_stat)
        try:
            inv_h_dot_g = spsolve(-h,g,assume_a="pos",check_finite=False)
        except (ValueError, LinAlgError) as e:
            if "infs or NaNs" in str(e):
                raise ConvergenceError(
                    """Hessian or gradient contains nan or inf value(s). Convergence halted. {0}""".format(CONVERGENCE_DOCS),
                    e,
                )
            elif isinstance(e, LinAlgError):
                raise ConvergenceError(
                    """Convergence halted due to matrix inversion problems. Suspicion is high collinearity. {0}""".format(
                        CONVERGENCE_DOCS
                    ),
                    e,
                )
            else:
                # something else?
                raise e

        delta = inv_h_dot_g
        current_app.logger.info(f'[API] delta: {delta}')
        hessian, gradient = h,g
        if delta.size > 0:
            norm_delta = norm(delta)
        else:
            norm_delta = 0

        current_app.logger.info(f'[API] norm_delta:{norm_delta}')

        newton_decrement = g.dot(inv_h_dot_g)/2

        #convergence criteria
        if norm_delta < precision:
            converging, success = False, True
        # this is what R uses by default
        elif newton_decrement < precision:
            converging, success = False, True
        #maximal number of iterations reached
        elif iteration>=max_steps:
            converging, success = False, False
        elif step_size <= 0.00001:
            converging, success = False, False

        step_size = step_sizer.update(norm_delta).next()
        redis_set('step_size',step_size)
        redis_set('step_sizer',step_sizer)
        redis_set('converging',converging)

        current_app.logger.info(f'[API] step_size: {step_size}')
        current_app.logger.info( f'[API] newton_decrement: {newton_decrement}' )


        beta += step_size * delta
        current_app.logger.info( f'[API] new updated beta: {beta}' )

        #redis_set('available',True)
        redis_set('beta',beta)
        redis_set('hessian',hessian)

        redis_set('global_stat',[]) # clear for new iteration

        #next_step() # -> send model parameter
        redis_set( 'step', 'send_model_parameter' )
        redis_set( 'available', True ) # send model parameter to slaves

    else:
        current_app.logger.info( '[API] Not the data of all clients has been send to the master' )

def get_efron_values(global_stat):
    """
    :param global_stat: aggregated statistics of all clients
    Calculate the hessian and gradient out of the aggregated statistics from the slaves.
    """

    current_app.logger.info( '[API] run get_efron_values' )

    zr = redis_get( 'global_zr' )
    covariates = zr.axes[ 0 ]
    d = len( covariates )

    global_i1 = {}
    global_i2 = {}
    global_i3 = {}

    current_app.logger.info( f'[API] global_stat: {global_stat}' )

    for client in global_stat:

        last_i1 = 0
        last_i2 = np.zeros( (d,) )
        last_i3 = np.zeros( (d, d) )

        # send sites an updated beta and sites calculate aggregated statistics
        i1 = client[ 0 ]
        i2 = client[ 1 ]
        i3 = client[ 2 ]

        D = redis_get( 'global_D' )
        count_d = redis_get( 'global_count_d' )

        for time in sorted( D, reverse=True ):
            t = str(float(time)) # in D there are ints but json makes out of integer keys -> string keys and in i1 there are strings of float numbers

            # if time already in i1 we can normally add the value of time to global_i1 or create a new key with the value in global_i1
            if t in i1:
                if t in global_i1:
                    df = global_i1[ t ]
                    global_i1[ t ] = df + i1[t]
                    i2_t = json.loads( i2[ t ] )
                    i2_t = np.array(i2_t)
                    df = global_i2[ t ]
                    global_i2[ t ] = df + i2_t
                    i3_t = json.loads( i3[ t ] )
                    i3_t = np.array( i3_t )
                    df = global_i3[ t ]
                    global_i3[ t ] = df + i3_t

                else:
                    i2_t = json.loads(i2[t])
                    i2_t = np.array( i2_t )
                    i3_t = json.loads(i3[t])
                    i3_t = np.array( i3_t )
                    global_i1[ t ] = i1[ t ]
                    global_i2[ t ] = i2_t
                    global_i3[ t ] = i3_t

                last_i1 = i1[ t ]
                last_i2 = i2_t
                last_i3 = i3_t
            # if time is not in i1 we have to add the value of the key time-1 of i1 to global_i1
            else:
                if t in global_i1:
                    global_i1[ t ] = global_i1[ t ] + last_i1
                    global_i2[ t ] = global_i2[ t ] + last_i2
                    global_i3[ t ] = global_i3[ t ] + last_i3
                else:
                    global_i1[ t ] = last_i1
                    global_i2[ t ] = last_i2
                    global_i3[ t ] = last_i3


    # calculate first and second order derivative
    d1 = np.zeros( (d,) )
    d2 = np.zeros( (d, d) )
    for time in D:
        t = str(float(time))
        Dki = count_d[ time ]
        numer = global_i2[ t ] #in global_i1 and global_i2 -> keys are strings
        denom = 1.0 / np.array( [ global_i1[ t ] ] )
        summand = numer * denom[ :, None ]
        d1 = d1 + Dki * summand.sum( 0 )
        a1 = global_i3[ t ] * denom
        a2 = np.dot( summand.T, summand )
        d2 = d2 + Dki * (a2 - a1)

    # first order derivative
    zr = zr.to_numpy()
    gradient = zr - d1
    hessian = d2

    #current_app.logger.info(f'[API] hessian: {hessian}')
    #current_app.logger.info( f'[API] gradient: {gradient}' )

    return hessian, gradient

def calculate_final_statistics():
    """

    :return: summary of results

    This method calculates the model parameter and some additional results (hazard ratios, confidence intervals, ...).
    """
    current_app.logger.info('[API] run calculate final statistics')
    beta = redis_get('beta')
    norm_std = redis_get('global_std')
    params_ = beta / norm_std.values
    zr = redis_get('global_zr')
    hessian = redis_get('hessian')
    params_ = pd.Series( params_, index=zr.axes[ 0 ], name="coef" )

    current_app.logger.info( f'[API] final model parameter: {params_} ' )

    hazard_ratios_ = pd.Series( np.exp(params_ ), index=zr.axes[ 0 ], name="exp(coef)" )
    alpha = 0.05
    variance_matrix_ = _calculate_variance_matrix( hessian, norm_std, zr)
    standard_errors_ = _calculate_standard_errors(variance_matrix_,params_)
    p_values_ = pd.Series(_calculate_p_values(params_,standard_errors_), index=zr.axes[ 0 ] )
    confidence_intervals_ = _calculate_confidence_intervals( alpha,params_,standard_errors_ )

    ci = 100 * (1 - alpha)
    z = inv_normal_cdf( 1 - alpha / 2 )
    with np.errstate( invalid="ignore", divide="ignore", over="ignore", under="ignore" ):
        df = pd.DataFrame( index=params_.index )
        df[ "coef" ] = params_
        df[ "exp(coef)" ] = hazard_ratios_
        df[ "se(coef)" ] = standard_errors_
        df[ "coef lower %g%%" % ci ] = confidence_intervals_[ "%g%% lower-bound" % ci ]
        df[ "coef upper %g%%" % ci ] = confidence_intervals_[ "%g%% upper-bound" % ci ]
        df[ "exp(coef) lower %g%%" % ci ] = hazard_ratios_ * np.exp( -z * standard_errors_ )
        df[ "exp(coef) upper %g%%" % ci ] = hazard_ratios_ * np.exp( z * standard_errors_ )
        df[ "z" ] = _calculate_z_values(params_,standard_errors_)
        df[ "p" ] = p_values_
        df[ "-log2(p)" ] = -np.log2( df[ "p" ] )

    redis_set('result',df)

    current_app.logger.info(f'[API] result dataframe: {df} ')

    #next_step() #-> send_to_slaves
    redis_set('step','send_to_slaves')

    redis_set('available',True) # master will send the summary results to the slaves

def _calculate_variance_matrix(hessian,norm_std,zr):
    """

    :param hessian: second order derivative
    :param norm_std: standard deviation
    :return: variance matrix
    """

    if hessian.size > 0:
        variance_matrix_ = pd.DataFrame(
            -np.linalg.inv( hessian ) / np.outer( norm_std, norm_std ), index=zr.axes[0],
            columns=zr.axes[0]
        )
    else:
        variance_matrix_ = pd.DataFrame( index=zr.axes[0], columns=zr.axes[0] )
    return variance_matrix_

def _calculate_standard_errors(variance_matrix_,params_):
    """

    :return: Pandas Series of the standard errors

    This method calculates the standard errors out of the variance matrix.
    """
    se = np.sqrt(variance_matrix_.values.diagonal() )
    return pd.Series( se, name="se", index=params_.index )

def _calculate_z_values(params_,standard_errors_) -> pd.Series:
    """

    :return: z-values

    This method calculates the z-values.
    """
    return params_ / standard_errors_

def _calculate_p_values(params_,standard_errors_) -> np.ndarray:
    """

    :return: pvalues

    This method calculates the pvalues.
    """
    U = _calculate_z_values(params_,standard_errors_) ** 2
    return stats.chi2.sf( U, 1 )

def _calculate_confidence_intervals(alpha,params_,standard_errors_) -> pd.DataFrame:
    """

    :param alpha: normally 0.05
    :return: confidence intervals (the 95% lower and upper bound)
    """
    ci = 100 * (1 - alpha)
    z = inv_normal_cdf( 1 - alpha / 2 )
    se = standard_errors_
    hazards = params_.values
    return pd.DataFrame(
        np.c_[hazards - z * se, hazards + z * se],
        columns=["%g%% lower-bound" % ci, "%g%% upper-bound" % ci],
        index=params_.index,
    )