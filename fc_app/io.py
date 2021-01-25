import yaml
from flask import current_app
from redis_util import redis_get, redis_set

INPUT_DIR = "/mnt/input"
OUTPUT_DIR = "/mnt/output"


def read_input():
    filename = redis_get('input_filename')
    try:
        current_app.logger.info('[API] Parsing data of ' + INPUT_DIR)
        current_app.logger.info('[API] ' + filename)

        file = open(INPUT_DIR + "/" + filename, "r")
        file_data = file.read()
        current_app.logger.info('[API] ' + str(file_data))
        data = list(map(float, file_data.strip().split(',')))

        return data
    except Exception as e:
        current_app.logger.info('[API] could not read files', e)

        return None


def write_results(result):
    # Write result
    try:
        current_app.logger.info("Write results to output folder:")
        file_write = open(OUTPUT_DIR + '/' + redis_get("output_filename"), 'x')
        file_write.write(str(result))
        file_write.close()
    except Exception as e:
        current_app.logger.error('Could not write result file.', e)

    # Check if file is damaged
    try:
        file_read = open(OUTPUT_DIR + '/' + redis_get("output_filename"), 'r')
        content = file_read.read()
        current_app.logger.info(content)
        file_read.close()
    except Exception as e:
        current_app.logger.error('There might be something wrong. The written file is not readable.', e)


def read_config():
    with open(INPUT_DIR + '/config.yml') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)['fc_mean']

        redis_set('input_filename', config['files']['input'])
        redis_set('output_filename', config['files']['output'])
