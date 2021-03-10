import errno
import json
import os
import sys
import shutil
import threading
import time

from app import config
from app.algo import local_computation, global_aggregation, write_results
from app.io import read_config, read_input


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
		self.expression_data = ''
		self.interaction_network = ''
		self.local_model = ''
		self.client_models = []
		self.global_model = ''

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

	def app_flow(self):
		# This method contains a state machine for the client and coordinator instance
		# Coordinator Workflow: 1 -> 2 -> 4 -> 5 -> 6 -> 7 -> 8
		# Client Workflow:      1 -> 2 -> 3 -> 4 -> 5 -> 7 -> 8

		# === States ===
		state_initialize = 1
		state_read_input = 2
		state_wait_for_config = 3
		state_local_computation = 4
		state_wait_for_global_aggregation = 5
		state_global_aggregation = 6
		state_write_results = 7
		state_finish = 8

		# Initial state
		state = state_initialize
		self.progress = 'initializing...'

		while True:

			if state == state_initialize:
				if self.id is not None:  # Test if setup has happened already
					config.init()  # initialize config dictionary
					config.add_option('id', self.id)
					config.add_option('is_coordinator', self.master)
					read_config(self.master)

					# create temp directory for python <-> R data exchange
					try:
						os.makedirs(config.get_option('TEMP_DIR'))
					except OSError as e:
						if e.errno != errno.EEXIST:
							print(f'[CRIT] Could not create temporary directory', flush=True)
							raise

					state = state_read_input

			if state == state_read_input:
				self.expression_data = read_input(config.get_option('expression_data_filepath'),
												  config.get_option('expression_data_filename'),
												  config.get_option('expression_data_separator'))
				if self.master:
					self.interaction_network = read_input(config.get_option('interaction_network_filepath'),
														  config.get_option('interaction_network_filename'),
														  config.get_option('interaction_network_separator'))
					print(f'[COORDINATOR] Sending interaction network to clients', flush=True)
					self.data_outgoing = json.dumps([config.get_option('grandforest_method'),
													 config.get_option('number_of_trees'),
													 self.interaction_network])
					self.status_available = True
					state = state_local_computation
				else:
					state = state_wait_for_config

			# LOCAL PART

			if state == state_wait_for_config:
				self.progress = 'gathering config...'
				if len(self.data_incoming) > 0:
					config.add_option('grandforest_method', self.data_incoming[0][0])
					config.add_option('number_of_trees', self.data_incoming[0][1])
					self.interaction_network = self.data_incoming[0][2]
					print(f'[CLIENT] Received config and interaction network with size {sys.getsizeof(self.interaction_network)} Bytes from coordinator', flush=True)
					state = state_local_computation

			if state == state_local_computation:
				self.progress = 'computing...'
				self.local_model = local_computation(self.expression_data, self.interaction_network)
				if self.master:
					print(f'[COORDINATOR] Finished computing the local model', flush=True)
					self.client_models.append(self.local_model)
				else:
					print(f'[CLIENT] Sending local model to master', flush=True)
					self.data_outgoing = json.dumps(self.local_model)
					self.data_incoming = []
					self.status_available = True

				state = state_wait_for_global_aggregation

			if state == state_wait_for_global_aggregation:
				if self.master:
					self.progress = f'gathering... {len(self.data_incoming)}/{len(self.clients) - 1} models received'
					if len(self.data_incoming) == len(self.clients) - 1:
						print(f'[COORDINATOR] Received local models from all clients', flush=True)
						self.client_models.extend(self.data_incoming)
						state = state_global_aggregation
				else:
					self.progress = 'gathering global model...'
					if len(self.data_incoming) > 0:
						self.global_model = self.data_incoming[0]
						print(f'[CLIENT] Received result from master', flush=True)
						state = state_write_results

			# GLOBAL PART

			if state == state_global_aggregation:
				self.progress = 'computing...'
				self.global_model = global_aggregation(self.data_incoming)
				print(f'[COORDINATOR] Sending global model to clients', flush=True)
				self.data_outgoing = json.dumps(self.global_model)
				self.status_available = True
				state = state_write_results

			if state == state_write_results:
				self.progress = 'writing results...'
				write_results(self.local_model, self.global_model)
				state = state_finish

			if state == state_finish:
				self.progress = 'finishing...'

				# delete temp directory with contents
				shutil.rmtree(config.get_option('TEMP_DIR'))

				time.sleep(10)
				print(f'[CLIENT/COORDINATOR] Finished the workflow, exiting...', flush=True)
				self.status_finished = True
				break

			time.sleep(0.1)


logic = AppLogic()
