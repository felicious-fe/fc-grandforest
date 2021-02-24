import json
import threading
import time
import os
import errno

from app.io import read_config
from app.algo import local_computation, global_aggregation, write_results
from app import config


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
        self.local_result = ''
        self.global_result = ''

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
        # This method contains a state machine for the slave and master instance

        # === States ===
        state_initializing = 1
        state_wait_for_config = 2
        state_local_gather = 3
        state_local_computation = 4
        state_global_gather = 5
        state_global_computation = 6
        state_finishing = 7

        # Initial state
        state = state_initializing
        self.progress = 'initializing...'

        while True:

            if state == state_initializing:
                if self.id is not None:  # Test if setup has happened already
                    config.init()  # initialize config dictionary
                    config.add_option('id', self.id)
                    config.add_option('is_coordinator', self.master)
                    read_config()

                    if self.master:

                        # Go to global part
                        state = state_global_gather
                    else:

                        # Go to local part
                        state = state_local_gather

                    # create temp directory for python <-> R data exchange
                    try:
                        os.makedirs(config.get_option('TEMP_DIR'))
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            print(f'[CRIT] Could not create temporary directory', flush=True)
                            raise

            # LOCAL PART

            if state == state_local_gather:
                self.progress = 'gathering...'
                self.iteration += 1

                if self.iteration == 1:
                    state = state_local_computation
                else:
                    if len(self.data_incoming) > 0:
                        self.global_result = self.data_incoming[0]
                        print(f'[CLIENT] Received result from master', flush=True)
                        state = state_finishing

            if state == state_local_computation:
                self.progress = 'computing...'
                self.local_result = local_computation()
                print(f'[CLIENT] Sending local model to master', flush=True)
                self.data_outgoing = json.dumps(self.local_result)
                self.status_available = True
                state = state_local_gather

            # GLOBAL PART

            if state == state_global_gather:
                self.progress = f'gathering... {len(self.data_incoming)}/{len(self.clients) - 1} models received'
                if len(self.data_incoming) == len(self.clients) - 1:
                    print(f'[COORDINATOR] Received local models from all clients', flush=True)
                    state = state_global_computation

            if state == state_global_computation:
                self.progress = 'computing...'
                self.global_result = global_aggregation(self.data_incoming)
                print(f'[COORDINATOR] Sending global model to clients', flush=True)
                self.data_outgoing = json.dumps(self.global_result)
                self.status_available = True
                state = state_finishing

            if state == state_finishing:
                self.progress = 'finishing...'
                write_results(self.local_result, self.global_result)
                time.sleep(10)
                print(f'[CLIENT/COORDINATOR] Finished the workflow, exiting...', flush=True)
                self.status_finished = True
                break

            time.sleep(0.1)


logic = AppLogic()
