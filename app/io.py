import base64
import os
import sys
import shutil
from uuid import uuid4

import yaml

from app import config
from app.RSubprocess import RSubprocess

INPUT_DIR = "/mnt/input"
TEMP_DIR = "/app/temp"
OUTPUT_DIR = "/mnt/output"


def read_input(input_filepath, input_filename, input_separator):
	"""
	Read in the input data from the input directory
	:return: Data or None if File could not be read
	"""
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)

	try:
		print('[IO] Parsing data of ' + input_filepath)

		command = ["/app/app/R/grandforest.read_data_frame.R",
				   input_filepath,
				   str(input_separator),
				   temp_path + "/" + input_filename + ".RData"]

		input_reader_subprocess = RSubprocess(command)
		print('[IO] Starting RSubprocess to read ' + input_filename + '...')
		input_reader_subprocess.start()
		print('[IO] Started RSubprocess to read ' + input_filename)
		input_reader_subprocess.join()
		print('[IO] Finished RSubprocess to read ' + input_filename)

		data = base64.b64encode(open(temp_path + "/" + input_filename + ".RData", 'rb').read()).decode('utf-8')
		print('[IO] Converted RSubprocess Result to a python binary object')

		print('[IO] Read R Dataframe with size ' + str(sys.getsizeof(data)) + 'Bytes')

		return data
	except Exception as e:
		print('[IO] could not read file', e)

		return None


def write_output(data, split, output_directory_name):
	# create output directory
	os.makedirs(split + '/' + output_directory_name)

	write_binary_file(base64.decodebytes(data.encode('utf-8')),
					  split + '/' + output_directory_name + '/' + 'model' + '.RData')

	command = ["/app/app/R/grandforest.analyze_results.R",
			   split + '/' + output_directory_name + '/' + 'model' + '.RData',
			   TEMP_DIR + '/' + 'interaction_network.RData',
			   split + '/' + output_directory_name + '/']

	print('[IO] Starting RSubprocess to analyze the ' + output_directory_name + '...')
	analyzing_results_subprocess = RSubprocess(command)
	analyzing_results_subprocess.start()
	print('[IO] Started RSubprocess to analyze the ' + output_directory_name)
	analyzing_results_subprocess.join()
	print('[IO] Finished RSubprocess to analyze the ' + output_directory_name)


def write_binary_file(data, filename):
	"""
	Write the results to the output directory
	:param data: binary data to be written as RData File
	:param filename: output filename
	:return: None
	"""
	try:
		print("[IO] Writing results to output folder.")
		output_file_writer = open(filename, 'wb')
		output_file_writer.write(data)
		output_file_writer.close()
	except Exception as e:
		print('[ERROR] Could not write result file ', filename, '.', e)


def read_config(is_coordinator):
	"""
	Read in the config.yml in the input directory. Save the parameters in redis.
	:return: None
	"""

	print('[IO] Read config file.')
	with open(INPUT_DIR + '/config.yml') as f:
		config_file = yaml.load(f, Loader=yaml.FullLoader)['fc_grandforest']

		config.add_option('INPUT_DIR', INPUT_DIR)
		config.add_option('TEMP_DIR', TEMP_DIR)
		config.add_option('OUTPUT_DIR', OUTPUT_DIR)

		if is_coordinator:
			config.add_option('grandforest_method', config_file['global_options']['grandforest_method'])
			config.add_option('grandforest_treetype', config_file['global_options']['grandforest_treetype'])
			config.add_option('number_of_trees', config_file['global_options']['number_of_trees'])
			config.add_option('seed', config_file['global_options']['seed'])
			if config_file['global_options']['interaction_network'] == 'biogrid':
				config.add_option('interaction_network_filename', 'biogrid')
				config.add_option('interaction_network_filepath', '/app/interaction_networks/biogrid.tsv')
				config.add_option('interaction_network_separator', '\t')
			elif config_file['global_options']['interaction_network'] == 'htridb':
				config.add_option('interaction_network_filename', 'htridb')
				config.add_option('interaction_network_filepath', '/app/interaction_networks/htridb.tsv')
				config.add_option('interaction_network_separator', '\t')
			elif config_file['global_options']['interaction_network'] == 'iid':
				config.add_option('interaction_network_filename', 'iid')
				config.add_option('interaction_network_filepath', '/app/interaction_networks/iid.tsv')
				config.add_option('interaction_network_separator', '\t')
			elif config_file['global_options']['interaction_network'] == 'regnetwork':
				config.add_option('interaction_network_filename', 'regnetwork')
				config.add_option('interaction_network_filepath', '/app/interaction_networks/regnetwork.tsv')
				config.add_option('interaction_network_separator', '\t')
			else:
				config.add_option('interaction_network_filename', config_file['global_options']['interaction_network'])
				config.add_option('interaction_network_filepath',
								  INPUT_DIR + '/' + config_file['global_options']['interaction_network'])
				config.add_option('interaction_network_separator',
								  config_file['global_options']['interaction_network_separator'])

			# Check if coordinator config options are set correctly
			if not config.get_option('grandforest_method') in {'supervised', 'unsupervised'}:
				print('[IO] Config File Error.')
				raise ValueError("grandforest_method can either be 'supervised' or 'unsupervised'")

			if not config.get_option('grandforest_treetype') in {'classification', 'regression', 'survival',
																 'probability'}:
				print('[IO] Config File Error.')
				raise ValueError(
					"grandforest_treetype can be 'classification', 'regression', 'survival' or 'probability'")

		# Client config options
		# local options
		if str(config_file['local_options']['prediction']) == 'True':
			config.add_option('prediction', True)
		elif str(config_file['local_options']['prediction']) == 'False':
			config.add_option('prediction', False)
		else:
			print('[IO] Config File Error.')
			raise ValueError("prediction can be 'True' or 'False'")

		# local files
		try:
			config.add_option('expression_data_dependent_variable_name',
						  config_file['local_files']['expression_data_dependent_variable_name'])
		except KeyError:
			pass

		try:
			config.add_option('expression_data_survival_event',
						  config_file['local_files']['expression_data_survival_event'])
			config.add_option('expression_data_survival_time',
							  config_file['local_files']['expression_data_survival_time'])
		except KeyError:
			pass

		config.add_option('expression_data_separator', config_file['local_files']['expression_data_separator'])
		config.add_option('expression_data_filename', config_file['local_files']['expression_data'])

		# split
		config.add_option('split_mode', config_file['split']['mode'])
		config.add_option('split_dir', config_file['split']['dir'])

		splits = {}

		if config.get_option('split_mode') == 'directory':
			splits = dict.fromkeys(
				[f.path for f in os.scandir(f'{INPUT_DIR}/{config.get_option("split_dir")}') if f.is_dir()])
		else:
			splits[INPUT_DIR + '/'] = None

		for split in splits.keys():
			os.makedirs(split.replace("/input/", "/output/"), exist_ok=True)

		shutil.copyfile(INPUT_DIR + '/config.yml', OUTPUT_DIR + '/config.yml')

		return splits
