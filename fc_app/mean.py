import os
from flask import current_app
from redis_util import redis_set, redis_get
import numpy as np


def read_input(input_dir: str):
    """
    Reads all files stored in 'input_dir'.
    :param input_dir: The input directory containing the files.
    :return: None
    """
    files = []
    try:
        current_app.logger.info('[API] Parsing data of ' + input_dir)
        for filename in os.listdir(input_dir):
            current_app.logger.info('[API] ' + filename)
            if filename.endswith(".csv") or filename.endswith(".txt"):
                file = open(input_dir + "/" + filename, "r")
                file_data = file.read()
                current_app.logger.info('[API] ' + str(file_data))
                files.append(list(map(float, file_data.strip().split(','))))
            else:
                continue
        return files
    except Exception as e:
        current_app.logger.info('[API] could not read files', e)


def calculate_global_mean():
    """
    Calculates the global mean of the data of all clients.
    :return: None
    """
    current_app.logger.info('[API] Calculate Global Mean')
    mean = 0
    number_samples = 1
    sum = 0
    counter = 0
    global_data = redis_get('global_data')
    for i in global_data:
        sum += i[mean] * i[number_samples]
        counter += i[number_samples]

    global_mean = sum / counter
    current_app.logger.info(f'[API] Global Mean: {global_mean}')
    redis_set('global_mean', str(global_mean))


def write_results(global_mean: float, output_dir: str):
    """
    Writes the results of global_mean (one number) to the output_directory.
    :param global_mean: Global mean calculated from the local means of the clients
    :param output_dir: String of the output directory. Usually /mnt/output
    :return: None
    """
    try:
        current_app.logger.info("Write results to output folder:")
        file_write = open(output_dir + '/result.txt', 'x')
        file_write.write(str(global_mean))
        file_write.close()
    except Exception as e:
        current_app.logger.error('Could not write result file.', e)
    try:
        file_read = open(output_dir + '/result.txt', 'r')
        content = file_read.read()
        current_app.logger.info(content)
        file_read.close()
    except Exception as e:
        current_app.logger.error('File could not be read. There might be something wrong.', e)


def calculate_local_mean():
    """
    Calculate the local mean of a client
    :return: the local mean and the number of samples
    """
    current_app.logger.info('[API] Calculate local mean')
    files = redis_get('files')

    if files is None:
        current_app.logger.info('[API] No data available')
        return None
    else:
        nr_samples = 0
        means = []
        for d in files:
            means.append(np.mean(d))
            nr_samples = nr_samples + len(d)
        local_mean = np.mean(means)
        client_id = redis_get('id')
        current_app.logger.info(f'[API] Local mean of client {client_id}: {local_mean} with {nr_samples} samples')

        return local_mean, nr_samples
