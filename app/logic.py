import errno
import json
import os
import sys
import threading
import time
import math
import shutil

from app import config
from app.algo import local_computation, global_aggregation, local_prediction, result_analysis, write_results
from app.io import get_input_filesizes, check_if_config_file_exists, read_config, read_config_from_frontend, read_input, check_config


class AppLogic:

	def __init__(self):
		# === Status of this app instance ===

		# Indicates whether there is data to share, if True make sure self.data_out is available
		self.status_available = False

		# Only relevant for master, will stop execution when True
		self.status_finished = False

		# === Parameters set during setup ===
		self.id = None
		self.master = None
		self.clients = None

		# === Data ===
		self.data_incoming = []
		self.data_outgoing = None

		# === Internals ===
		self.thread = None
		self.iteration = 0
		self.progress = 'not started yet'
		self.input_form = None
		self.interaction_network = ''
		self.split_expression_data = {}
		self.local_models = {}
		self.client_models = []
		self.global_models = {}

	def handle_setup(self, client_id, master, clients):
		# This method is called once upon startup and contains information about the execution context of this instance
		self.id = client_id
		self.master = master
		self.clients = clients
		print(f'Received setup: {self.id} {self.master} {self.clients}', flush=True)

		self.thread = threading.Thread(target=self.app_flow)
		self.thread.start()

	def handle_incoming(self, data):
		# This method is called when new data arrives
		self.data_incoming.append(json.load(data))

	def handle_outgoing(self):
		# This method is called when data is requested
		self.status_available = False
		return self.data_outgoing

	def create_splits(self):
		# This method creates splits from folders in the input directory
		splits = {}

		if config.get_option('split_mode') == 'directory':
			splits = dict.fromkeys(
				[f.path for f in os.scandir(f'{config.get_option("INPUT_DIR")}/{config.get_option("split_dir")}') if
				 f.is_dir()])
		else:
			splits[config.get_option("INPUT_DIR") + '/'] = None

		for split in splits.keys():
			os.makedirs(split.replace("/input/", "/output/"), exist_ok=True)

		if check_if_config_file_exists():
			shutil.copyfile(config.get_option('INPUT_DIR') + '/config.yml', config.get_option('OUTPUT_DIR') + '/config.yml')

		self.split_expression_data = splits

	def app_flow(self):
		# This method contains a state machine for the client and coordinator instance
		# Coordinator Workflow: 1 -> 2 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9
		# Client Workflow:      1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 8 -> 9

		# === States ===
		state_initialize = 1
		state_read_config = 2
		state_wait_for_config = 3
		state_read_input = 4
		state_local_computation = 5
		state_wait_for_global_aggregation = 6
		state_global_aggregation = 7
		state_write_results = 8
		state_finish = 9

		# Initial state
		state = state_initialize
		self.progress = 'initializing'

		while True:

			# INITIALIZE THE WORKFLOW

			if state == state_initialize:
				if self.id is not None:  # Test if setup has happened already
					config.init()  # initialize config dictionary
					config.add_option('id', self.id)
					config.add_option('is_coordinator', self.master)
					
					# If config does not exist, wait for correct input in the frontend
					if check_if_config_file_exists():
						self.progress = 'parsing config file'
						read_config(self.master)
						self.create_splits()
					else:
						print('[IO] No config file found. Waiting for user input in the FrontEnd...')
						config_is_valid = False
						while config_is_valid is False:
							config.add_option('input_form', False)
							self.progress = 'getting config frontend'
							while config.get_option('input_form') is False:
								time.sleep(10)

							self.progress = 'parsing config frontend'
							print('[IO] Received FrontEnd Input Form. Continuing GrandForest workflow...')
							read_config_from_frontend(self.master, config.get_option('input_form'))
							self.create_splits()
							if check_config(self.split_expression_data):
								config_is_valid = True

					self.local_models = dict.fromkeys(self.split_expression_data.keys())

					# create temp directory for python <-> R data exchange
					# TODO create RAMDISK instead?
					try:
						os.makedirs(config.get_option('TEMP_DIR'))
					except OSError as e:
						if e.errno != errno.EEXIST:
							print(f'[CRIT] Could not create temporary directory', flush=True)
							raise

				# Set Expression Data Sample Size for Model Balancing
				if self.master:
					self.data_incoming.append([self.id, get_input_filesizes(self.split_expression_data)])
					state = state_read_config
				else:
					self.data_outgoing = json.dumps([self.id, get_input_filesizes(self.split_expression_data)])
					self.status_available = True
					state = state_wait_for_config

			# READ CONFIG AND SEND GLOBAL OPTIONS TO CLIENTS

			if state == state_read_config:
				self.progress = 'sending config'

				# Prepare and Send global options from the configuration to all clients
				#  including balanced amount of trees to be trained
				if self.master:
					print(self.data_incoming, ";; ", str(self.clients))
					if len(self.data_incoming) == len(self.clients):
						print(f'[CLIENT] Received all client expression data filesizes.', flush=True)
						filesizes_combined = dict()
						for participant in self.data_incoming:
							for split in self.split_expression_data.keys():
								try:
									filesizes_combined[split]
								except KeyError:
									filesizes_combined[split] = 0
								filesizes_combined[split] = filesizes_combined[split] + participant[1][split]

						num_trees_per_client_per_split = dict()
						for participant in self.data_incoming:
							for split in self.split_expression_data.keys():
								try:
									num_trees_per_client_per_split[participant[0]]
								except KeyError:
									num_trees_per_client_per_split[participant[0]] = dict()

								try:
									num_trees_per_client_per_split[participant[0]][split]
								except KeyError:
									num_trees_per_client_per_split[participant[0]][split] = 0
								num_trees_per_client_per_split[participant[0]][split] = math.ceil(
									participant[1][split] / filesizes_combined[split] * int(config.get_option('number_of_trees')))

						self.interaction_network = read_input(config.get_option('interaction_network_filepath'),
															  config.get_option('interaction_network_filename'),
															  config.get_option('interaction_network_separator'))
						config.add_option('number_of_trees_per_split', num_trees_per_client_per_split[self.id])
						self.data_incoming = []

						print(f'[COORDINATOR] Sending interaction network to clients', flush=True)
						self.data_outgoing = json.dumps([config.get_option('grandforest_method'),
														 config.get_option('grandforest_treetype'),
														 num_trees_per_client_per_split,
														 config.get_option('minimal_node_size'),
														 config.get_option('seed'),
														 self.interaction_network])
						self.status_available = True
						state = state_read_input
				else:
					state = state_wait_for_config
				
			# WAIT FOR CONFIG

			if state == state_wait_for_config:
				self.progress = 'gathering config'
				if len(self.data_incoming) > 0:
					config.add_option('grandforest_method', self.data_incoming[0][0])
					config.add_option('grandforest_treetype', self.data_incoming[0][1])
					config.add_option('number_of_trees_per_split', self.data_incoming[0][2][self.id])
					config.add_option('minimal_node_size', self.data_incoming[0][3])
					config.add_option('seed', self.data_incoming[0][4])
					self.interaction_network = self.data_incoming[0][5]
					print(f'[CLIENT] Received config and interaction network with size {sys.getsizeof(self.interaction_network)} Bytes from coordinator', flush=True)
					self.data_incoming = []
					state = state_read_input

			# READ INPUT FILES IN R

			if state == state_read_input:
				for split in self.split_expression_data.keys():
					self.split_expression_data[split] = read_input(split + '/' + config.get_option('expression_data_filename'),
													config.get_option('expression_data_filename'),
													config.get_option('expression_data_separator'))
				state = state_local_computation

			# COMPUTE LOCAL MODEL IN R

			if state == state_local_computation:
				self.progress = 'computing'

				# Check if config is valid
				#  this could be outsourced to io.py, since the frontend configuration is already checked there
				if config.get_option('grandforest_method') == "supervised":
					if config.get_option('grandforest_treetype') == "survival":
						try:
							config.get_option('expression_data_survival_event')
							config.get_option('expression_data_survival_time')
						except KeyError:
							print('[LOGIC] Config File Error.')
							raise ValueError("The GrandForest Layout is invalid: survival time and/or event missing")
						config.add_option('expression_data_dependent_variable_name', "None")
					else:
						try:
							config.get_option('expression_data_dependent_variable_name')
						except KeyError:
							print('[LOGIC] Config File Error.')
							raise ValueError("The GrandForest Layout is invalid: dependent variable name missing")
						config.add_option('expression_data_survival_event', "None")
						config.add_option('expression_data_survival_time', "None")

				for split in self.split_expression_data.keys():
					self.local_models[split] = local_computation(self.split_expression_data[split], self.interaction_network, split)

				if self.master:
					print(f'[COORDINATOR] Finished computing the local model', flush=True)
					self.client_models.append(self.local_models)
				else:
					print(f'[CLIENT] Sending local model to master', flush=True)
					self.data_outgoing = json.dumps(self.local_models)
					self.data_incoming = []
					self.status_available = True

				state = state_wait_for_global_aggregation

			# WAIT FOR GLOBAL AGGREGATION

			if state == state_wait_for_global_aggregation:
				if self.master:
					self.progress = 'gathering models'
					if len(self.data_incoming) == len(self.clients) - 1:
						print(f'[COORDINATOR] Received local models from all clients', flush=True)
						self.client_models.extend(self.data_incoming)
						self.data_incoming = []
						state = state_global_aggregation
				else:
					self.progress = 'gathering global model'
					if len(self.data_incoming) > 0:
						self.global_models = self.data_incoming[0]
						self.data_incoming = []
						print(f'[CLIENT] Received result from master', flush=True)
						state = state_write_results

			# GLOBAL AGGREGATION IN R

			if state == state_global_aggregation:
				self.progress = 'computing'
				for split in self.split_expression_data.keys():
					self.global_models[split] = global_aggregation([client_splits[split] for client_splits in self.client_models])
				print(f'[COORDINATOR] Sending global model to clients', flush=True)
				self.data_outgoing = json.dumps(self.global_models)
				self.status_available = True
				state = state_write_results

			# WRITE AND ANALYZE RESULTS IN R

			if state == state_write_results:
				self.progress = 'writing results'
				for split in self.split_expression_data.keys():
					if config.get_option('prediction'):
						local_prediction(self.global_models[split], self.split_expression_data[split], split.replace("/input/", "/output/"))
					write_results(self.local_models[split], self.global_models[split], split.replace("/input/", "/output/"))
					result_analysis(self.local_models[split], self.global_models[split], self.interaction_network,
									self.split_expression_data[split], split.replace("/input/", "/output/"))

				if self.master:
					self.data_incoming = ['DONE']
				else:
					self.data_outgoing = json.dumps('DONE')
					self.status_available = True
				state = state_finish
			
			# FINISH THE WORKFLOW

			if state == state_finish:
				self.progress = 'finishing'
				if self.master:
					if len(self.data_incoming) == len(self.clients):
						# FINISH COORDINATOR						
						print(f'[COORDINATOR] Finished the workflow, exiting...', flush=True)
						self.status_finished = True
						break
				else:
					# FINISH CIENT
					print(f'[CLIENT] Finished the workflow, exiting...', flush=True)
					self.status_finished = True
					break

			time.sleep(0.1)


logic = AppLogic()
