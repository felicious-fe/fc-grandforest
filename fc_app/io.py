import yaml
from flask import current_app
import pandas as pd

from redis_util import redis_get, redis_set

INPUT_DIR = "/mnt/input"
OUTPUT_DIR = "/mnt/output"


def read_input(redis_identifier):
    """
    Read in the input data from the input directory
    :return: Data or None if File could not be read
    """
    input_filename = redis_get(redis_identifier)
    try:
        current_app.logger.info('[IO] Parsing data of ' + INPUT_DIR)
        current_app.logger.info('[IO] ' + input_filename)

        #TODO: This is dirty code
        #data = pd.DataFrame.from_csv(INPUT_DIR + "/" + input_filename, sep='\t')
        if input_filename == 'expression_data_filename':
            data = pd.read_csv(INPUT_DIR + "/" + input_filename, sep=";", low_memory=False, index_col=None)
        else:
            data = pd.read_csv(INPUT_DIR + "/" + input_filename, sep='\t', dtype={"gene1": str, "gene2": str}, index_col=None)
        current_app.logger.info('[IO] Read Dataframe with dimensions ' + str(data.shape[0]) + ' x ' + str(data.shape[1]))

        return data
    except Exception as e:
        current_app.logger.error('[IO] could not read file', e)

        return None


def write_results(local_model, global_model):
    """
    Write the results to the output directory
    :param local_model: locally trained model result to be written as RData File
    :param global_model: globally aggregated model result to be written as RData File
    :return: None
    """
    try:
        current_app.logger.info("[IO] Write results to output folder.")
        output_file_writer1 = open(OUTPUT_DIR + '/' + redis_get("local_model_output_filename"), 'xb')
        output_file_writer1.write(local_model)
        output_file_writer1.close()

        output_file_writer2 = open(OUTPUT_DIR + '/' + redis_get("global_model_output_filename"), 'xb')
        output_file_writer2.write(global_model)
        output_file_writer2.close()
    except Exception as e:
        current_app.logger.error('[IO] Could not write result files.', e)


def read_config():
    """
    Read in the config.yml in the input directory. Save the parameters in redis.
    :return: None
    """
    current_app.logger.info('[IO] Read config file.')
    with open(INPUT_DIR + '/config.yml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)['fc_grandforest']

        redis_set('expression_data_filename', config['files']['expression_data'])
        redis_set('interaction_network_filename', config['files']['interaction_network'])
        redis_set('local_model_output_filename', config['files']['local_model_output'])
        redis_set('global_model_output_filename', config['files']['global_model_output'])
