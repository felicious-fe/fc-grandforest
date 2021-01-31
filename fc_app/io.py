import yaml
from flask import current_app

from redis_util import redis_get, redis_set

INPUT_DIR = "/mnt/input"
OUTPUT_DIR = "/mnt/output"


def read_input():
    """
    Read in the input data from the input directory
    :return: Data or None if File could not be read
    """
    filename = redis_get('input_filename')
    try:
        current_app.logger.info('[IO] Parsing data of ' + INPUT_DIR)
        current_app.logger.info('[IO] ' + filename)

        file = open(INPUT_DIR + "/" + filename, "r")
        file_data = file.read()
        current_app.logger.info('[IO] ' + str(file_data))
        data = list(map(float, file_data.strip().split(',')))

        return data
    except Exception as e:
        current_app.logger.error('[IO] could not read file', e)

        return None


def write_results(result):
    """
    Write the results to the output directory
    :param result: result to be written
    :return: None
    """
    try:
        current_app.logger.info("[IO] Write results to output folder.")
        file_write = open(OUTPUT_DIR + '/' + redis_get("output_filename"), 'x')
        file_write.write(result)
        file_write.close()
    except Exception as e:
        current_app.logger.error('[IO] Could not write result file.', e)


def read_config():
    """
    Read in the config.yml in the input directory. Save the parameters in redis.
    :return: None
    """
    current_app.logger.info('[IO] Read config file.')
    with open(INPUT_DIR + '/config.yml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)['fc_mean']

        redis_set('input_filename', config['files']['input'])
        redis_set('output_filename', config['files']['output'])
