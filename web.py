import redis
import rq
from flask import Blueprint, current_app, render_template, request, send_file, Response
from fc_app.api import local_normalization, redis_get, redis_set,preprocessing
import pandas as pd
from io import BytesIO
from matplotlib.figure import Figure
from lifelines.utils import inv_normal_cdf
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas


r = redis.Redis(host='localhost', port=6379, db=0)
tasks = rq.Queue('fc_tasks', connection=r)
web_bp = Blueprint('web', __name__)
#steps = ['setup_master','send_to_slave','setup_slave', 'preprocessing','local_norm', 'send_to_master', 'global_norm', 'normalization','local_init','send_to_master','global_init','local_stat','send_to_master','update_beta','send_model_parameter','summary','final']


@web_bp.route('/', methods=['GET'])
def root():
    """
    decides which HTML page content will be shown to the user
    :return: step == 'start': the setup is not yet finished and the program cannot start yet
             step == 'setup_master': master can define parameters and upload data
             step == 'setup_slave': client can upload data
             step == 'final': the results of the global mean will be shown
             else: the calculations are not yet finished
    """
    step = redis_get('step')
    if step == 'start':
        return render_template('setup.html')
    elif step == 'setup_master':
        current_app.logger.info('[WEB] Before rendering start_client.html')
        if redis_get('master'):
            return render_template('start_master.html')
        else:
            return render_template('setup.html')
    elif step=='setup_slave':
        if not redis_get('master'):
            max_steps = redis_get('max_steps')
            precision = redis_get('precision')
            duration_col = redis_get('duration_col')
            event_col = redis_get('event_col')
            covariates = redis_get('covariates')
            covariates = ','.join(covariates)
            return render_template('start_client.html',max_steps = max_steps, precision = precision, duration_col = duration_col, event_col = event_col, covariates = covariates)
        else:
            return render_template('calculations.html')
    elif step == 'final':
        result = redis_get('result')
        result_html = result.to_html(classes='data',header='true')
        return render_template('final.html',tables=[result_html])
    else:
        return render_template('calculations.html')

@web_bp.route('/params', methods=['GET'])
def params():
    """
    :return: current parameter values as a HTML page
    """
    master = redis_get('master')
    step = redis_get('step')
    local_norm = redis_get('local_norm')
    global_norm = redis_get('global_norm')
    data = redis_get('data')
    available = redis_get('available')
    return f"""
        master: {master}
        step: {step}
        local normalization: {local_norm}
        global normalization: {global_norm}
        data: {data}
        available: {available}
        """

@web_bp.route('/run', methods=['POST'])
def run():
    """
    POST request to /run with the data as a file
    step == 'setup_master': the file of the master will be read and some parameters will be saved
    step == 'setup_client': the file of the clients will be read
    step == 'final': calculations are done, a GET request to '/' will be send
    else: a message for the relevant step will be shown
    :return: HTML page with content to the relevant step
    """
    cur_step = redis_get('step')
    if cur_step == 'start':
        current_app.logger.info('[WEB] POST request to /run in step "start" -> wait setup not finished')
        return 'Wait until setup is done'
    elif cur_step == 'setup_master':
        if redis_get('master'):
            current_app.logger.info('[WEB] POST request to /run in step "setup" -> read data')
            current_app.logger.info('[WEB] Upload file')
            current_app.logger.info('[WEB] Select duration and event columns')
            result = request.form
            if 'file' in request.files:
                file = request.files['file']
                file_type = result[ 'file_type' ]
                if file_type=='csv':
                    data = pd.read_csv(file,sep=',',encoding="latin-1")
                elif file_type=='tsv':
                    data = pd.read_csv( file, sep='\t', encoding="latin-1" )
                current_app.logger.info(f'[WEB] data: {data}')
                redis_set('data', data)
                current_app.logger.info('[WEB] File successfully uploaded and processed')

                duration_col = result['duration_col']
                event_col = result['event_col']

                max_steps = result['max_steps']
                precision = result['precision']
                redis_set('max_steps',int(max_steps))
                redis_set('precision',float(precision))

                if (duration_col is None or event_col is None):
                    current_app.logger.info( '[WEB] No duration or event column specified ' )
                    return render_template('empty.html')
                else:
                    current_app.logger.info( f'[WEB] duration_col: {duration_col}' )
                    redis_set('duration_col',duration_col)
                    current_app.logger.info( f'[WEB] event_col: {event_col}' )
                    redis_set('event_col',event_col)

                    current_app.logger.info('[WEB] Duration and event columns successfully uploaded')

                    #next_step() # -> send_to_slave
                    redis_set('step','send_to_slave')
                    redis_set('available',True)
                    return render_template('calculations.html')


            else:
                current_app.logger.info('[WEB] No File was uploaded')
                return render_template('empty.html')

    elif cur_step == 'setup_slave':
        if not redis_get('master'):
            current_app.logger.info( '[WEB] POST request to /run in step "setup" -> read data' )
            current_app.logger.info( '[WEB] Upload file' )
            current_app.logger.info( '[WEB] Select duration and event columns' )
            result = request.form
            if 'file' in request.files:
                file = request.files[ 'file' ]
                file_type = result[ 'file_type' ]
                if file_type == 'csv':
                    data = pd.read_csv( file, sep=',', encoding="latin-1" )
                elif file_type == 'tsv':
                    data = pd.read_csv( file, sep='\t', encoding="latin-1" )
                current_app.logger.info( f'[WEB] data: {data}' )
                redis_set( 'data', data )
                current_app.logger.info( '[WEB] File successfully uploaded and processed' )

                #next_step() # -> preprocessing
                redis_set('step','preprocessing')
                redis_set('master_step','master_norm')
                redis_set('slave_step','slave_norm')
                preprocessing()
                return render_template( 'calculations.html' )

            else:
                current_app.logger.info( '[WEB] No File was uploaded' )
                return render_template( 'empty.html' )

    elif cur_step == 'final':
        current_app.logger.info('[WEB] POST request to /run in step "final" -> GET request to "/"')
        # TODO weiterleitung zu route /
        result = redis_get( 'results' )
        result_html = result.to_html( classes='data', header='true' )
        return render_template( 'final.html', tables=[ result_html ] )
    else:
        current_app.logger.info(f'[WEB] POST request to /run in step "{cur_step}" -> wait calculations not finished')
        return render_template('calculations.html')


@web_bp.route('/download_results')
def download_results():
    result = redis_get('result')
    file_data = result.to_csv(sep='\t').encode()
    return send_file(BytesIO(file_data), attachment_filename='results.csv', as_attachment=True)

@web_bp.route('/plot.png')
def download_plot():
    result = redis_get('result')
    params_ = result[ 'coef' ]
    standard_errors_ = result[ 'se(coef)' ]
    fig = create_figure(params_,standard_errors_)
    output = BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(),mimetype='image/png')

def create_figure(params_,standard_errors_):
    fig = Figure()
    axis = fig.add_subplot(1,1,1)
    axis = plot(params_, standard_errors_, ax=axis )
    return fig

def plot(params_, standard_errors_, ax=None, **errorbar_kwargs):
    """
    Produces a visual representation of the coefficients (i.e. log hazard ratios), including their standard errors and magnitudes.

    Parameters
    ----------
    columns : list, optional
        specify a subset of the columns to plot
    hazard_ratios: bool, optional
        by default, ``plot`` will present the log-hazard ratios (the coefficients). However, by turning this flag to True, the hazard ratios are presented instead.
    errorbar_kwargs:
        pass in additional plotting commands to matplotlib errorbar command

    Returns
    -------
    ax: matplotlib axis
        the matplotlib axis that be edited.

    """
    from matplotlib import pyplot as plt

    if ax is None:
        ax = plt.gca()

    alpha = 0.05

    errorbar_kwargs.setdefault( "c", "k" )
    errorbar_kwargs.setdefault( "fmt", "s" )
    errorbar_kwargs.setdefault( "markerfacecolor", "white" )
    errorbar_kwargs.setdefault( "markeredgewidth", 1.25 )
    errorbar_kwargs.setdefault( "elinewidth", 1.25 )
    errorbar_kwargs.setdefault( "capsize", 3 )

    z = inv_normal_cdf( 1 - alpha / 2 )
    user_supplied_columns = True


    user_supplied_columns = False
    columns = params_.index

    yaxis_locations = list( range( len( columns ) ) )
    log_hazards = params_.loc[ columns ].values.copy()

    order = list( range( len( columns ) - 1, -1, -1 ) ) if user_supplied_columns else np.argsort( log_hazards )


    symmetric_errors = z * standard_errors_[ columns ].values
    ax.errorbar( log_hazards[ order ], yaxis_locations, xerr=symmetric_errors[ order ], **errorbar_kwargs )
    ax.set_xlabel( "log(HR) (%g%% CI)" % ((1 - alpha) * 100) )

    best_ylim = ax.get_ylim()
    ax.vlines(0, -2, len( columns ) + 1, linestyles="dashed", linewidths=1, alpha=0.65 )
    ax.set_ylim( best_ylim )

    tick_labels = [ columns[ i ] for i in order ]

    ax.set_yticks( yaxis_locations )
    ax.set_yticklabels( tick_labels )
    ax.set_title("Visual representation of the coefficients of the federated model (log(hazard ratio))")

    return ax