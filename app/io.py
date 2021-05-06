import base64
import os
import sys
import shutil
from uuid import uuid4

from bottle import FormsDict

import yaml

from app import config
from app.RSubprocess import RSubprocess

INPUT_DIR = "/mnt/input"
TEMP_DIR = "/tmp/featurecloud"
OUTPUT_DIR = "/mnt/output"


def get_input_filesizes(splits):
	filesizes = dict()
	for split in splits.keys():
		with open(split + '/' + config.get_option('expression_data_filename')) as file:
			filesizes[split] = sum(1 for _ in file)
	return filesizes


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


def write_output(model, model_name, split):
	"""
	Write the results to the output directory
	:param model: binary data to be written as RData File
	:param model_name: model name ('local_model' or 'global_model')
	:param split: current split
	:return: None
	"""
	print("[IO] Writing results to output folder.")
	# create output directory
	os.makedirs(split + '/' + model_name)
	open(split + '/' + model_name + '/' + 'model' + '.RData', 'wb').write(
		base64.decodebytes(model.encode('utf-8')))


def check_if_config_file_exists():
	return os.path.isfile(INPUT_DIR + '/config.yml')


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
		config.add_option('minimal_node_size', config_file['global_options']['minimal_node_size'])
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


def read_config_from_frontend(is_coordinator, conf_input: FormsDict):
	"""
	Read in the config.yml in the input directory. Save the parameters in redis.
	:return: None
	"""

	print('[IO] Parsing config from Frontend.')

	config.add_option('INPUT_DIR', INPUT_DIR)
	config.add_option('TEMP_DIR', TEMP_DIR)
	config.add_option('OUTPUT_DIR', OUTPUT_DIR)

	if is_coordinator:
		if conf_input.get('grandforest_method')[0] == 's':
			config.add_option('grandforest_method', 'supervised')
		else:
			config.add_option('grandforest_method', 'unsupervised')
		config.add_option('grandforest_treetype', conf_input.get('grandforest_method')[2:])
		config.add_option('number_of_trees', conf_input.get('number_of_trees'))
		config.add_option('minimal_node_size', conf_input.get('minimal_node_size'))
		config.add_option('seed', conf_input.get('seed'))
		if conf_input.get('interaction_network') == 'biogrid':
			config.add_option('interaction_network_filename', 'biogrid')
			config.add_option('interaction_network_filepath', '/app/interaction_networks/biogrid.tsv')
			config.add_option('interaction_network_separator', '\t')
		elif conf_input.get('interaction_network') == 'htridb':
			config.add_option('interaction_network_filename', 'htridb')
			config.add_option('interaction_network_filepath', '/app/interaction_networks/htridb.tsv')
			config.add_option('interaction_network_separator', '\t')
		elif conf_input.get('interaction_network') == 'iid':
			config.add_option('interaction_network_filename', 'iid')
			config.add_option('interaction_network_filepath', '/app/interaction_networks/iid.tsv')
			config.add_option('interaction_network_separator', '\t')
		elif conf_input.get('interaction_network') == 'regnetwork':
			config.add_option('interaction_network_filename', 'regnetwork')
			config.add_option('interaction_network_filepath', '/app/interaction_networks/regnetwork.tsv')
			config.add_option('interaction_network_separator', '\t')
		else:
			config.add_option('interaction_network_filename', conf_input.get('interaction_network_file_name'))
			config.add_option('interaction_network_filepath',
								INPUT_DIR + '/' + conf_input.get('interaction_network_file_name'))
			config.add_option('interaction_network_separator', conf_input.get('interaction_network_separator').replace('\\t', '\t'))

	# Client config options
	# local options
	if str(conf_input.get('prediction')) == 'True':
		config.add_option('prediction', True)
	elif str(conf_input.get('prediction')) == 'False':
		config.add_option('prediction', False)
	else:
		print('[IO] Config File Error.')
		raise ValueError("prediction can be 'True' or 'False'")

	# local files
	try:
		config.add_option('expression_data_dependent_variable_name',
						conf_input.get('expression_data_dependent_variable_name'))
	except KeyError:
		pass

	try:
		config.add_option('expression_data_survival_event',
						conf_input.get('expression_data_survival_event'))
		config.add_option('expression_data_survival_time',
						conf_input.get('expression_data_survival_time'))
	except KeyError:
		pass

	config.add_option('expression_data_separator', conf_input.get('expression_data_separator').replace('\\t', '\t'))
	config.add_option('expression_data_filename', conf_input.get('expression_data_file'))

	# split
	config.add_option('split_mode', conf_input.get('split_mode'))
	config.add_option('split_dir', conf_input.get('split_dir'))


def check_config(splits):
	# Test text variables
	try:
		int(config.get_option('number_of_trees'))
	except ValueError:
		print('[IO] Config File Error.')
		print(f"Number of Trees variable is not a valid number: {config.get_option('number_of_trees')}")
		return False

	try:
		int(config.get_option('minimal_node_size'))
	except ValueError:
		print('[IO] Config File Error.')
		print(f"Minimal Node Size variable is not a valid number: {config.get_option('minimal_node_size')}")
		return False

	if config.get_option('seed') != 'None' and config.get_option('seed') is not None:
		try:
			int(config.get_option('seed'))
		except ValueError:
			print('[IO] Config File Error.')
			print(f"Seed variable is not a valid number: {config.get_option('seed')}")
			return False

	# Test interaction network file
	try:
		open(config.get_option('interaction_network_filepath'), 'r')
	except FileNotFoundError:
		print('[IO] Config File Error.')
		print(f"Interaction Network File {config.get_option('interaction_network_filename')} not found.")
		return False

	# Test expression data files in each split
	for split in splits.keys():
		try:
			open(split + '/' + config.get_option('expression_data_filename'), 'r')
		except FileNotFoundError:
			print('[IO] Config File Error.')
			print(f"Expression data File {config.get_option('expression_data_filename')} not found.")
			return False

		with open(split + '/' + config.get_option('expression_data_filename'), 'r') as file:
			firstline = file.readline()
			if config.get_option('grandforest_treetype') == 'survival':
				if firstline.find(config.get_option("expression_data_survival_event")) == -1 or firstline.find(config.get_option("expression_data_survival_time")) == -1:
					print('[IO] Config File Error.')
					print(f"expression_data_survival_event {config.get_option('expression_data_survival_event')} or expression_data_survival_time {config.get_option('expression_data_survival_time')} not found in Expression data File {config.get_option('expression_data_filename')}.")
					return False

			else:
				if firstline.find(config.get_option("expression_data_dependent_variable_name")) == -1:
					print('[IO] Config File Error.')
					print(f"expression_data_dependent_variable_name {config.get_option('expression_data_dependent_variable_name')} not found in Expression data File {config.get_option('expression_data_filename')}.")
					return False
	return True


def create_html_figures():
	figures = {}
	svg_start = '<svg width="100" height="100">'
	svg_end = '</svg>'

	figures['feature_importance_plot_importances'] = svg_start + open(config.get_option("OUTPUT_DIR") + '/global_model/feature_importances.svg').read() + svg_end
	figures['feature_importance_plot_network'] = svg_start + open(config.get_option("OUTPUT_DIR") + '/global_model/interaction_subnetwork.svg').read() + svg_end
	figures['endophenotypes_plot_heatmap'] = svg_start + open(config.get_option("OUTPUT_DIR") + '/global_model/patient_clustering_heatmap.svg').read() + svg_end
	try:
		figures['endophenotypes_plot_survival'] = svg_start + open(config.get_option("OUTPUT_DIR") + '/global_model/patient_clustering_survival.svg').read() + svg_end
	except FileNotFoundError:
		figures['endophenotypes_plot_survival'] = ""
	return figures


def tsv_to_html(filename, sep):
	html = "<table>"
	with open(filename, 'r') as file:
		html = html + "<tr>"
		line = file.readline().split(sep)
		for val in line:
			html = html + f"<td>{val}</td>"
		html = html + "</tr>"
	html = html + "</table>"
	return html


def create_html_tables():
	tables = {}
	tables['feature_importance_table'] = tsv_to_html(config.get_option("OUTPUT_DIR") + '/global_model/feature_importances.tsv', sep="\t")
	try:
		tables['prediction_results_table'] = tsv_to_html(config.get_option("OUTPUT_DIR") + '/Y_pred.tsv', sep="\t")
	except FileNotFoundError:
		tables['prediction_results_table'] = ""
	return tables


def create_result_html():
	figures = create_html_figures()
	tables = create_html_tables()

	result_html = open("/app/app/templates/result.tpl", 'r').read()

	r"{{\S*}}"


