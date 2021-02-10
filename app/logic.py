import json
import random
import threading
import time


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
        state_local_gather = 2
        state_local_computation = 3
        state_global_gather = 4
        state_global_computation = 5
        state_finishing = 6

        # Initial state
        state = state_initializing
        self.progress = 'initializing...'

        while True:

            if state == state_initializing:
                if self.id is not None:  # Test is setup has happened already
                    if self.master:
                        # Go to global part
                        state = state_global_gather
                    else:
                        # Go to local part
                        state = state_local_gather

            # LOCAL PART

            if state == state_local_gather:
                self.progress = 'gathering...'
                self.iteration += 1

                if self.iteration == 1:
                    state = state_local_computation
                else:
                    if len(self.data_incoming) > 0:
                        print(f'[SLAVE] Got result from master: {self.data_incoming[0]}', flush=True)
                        break

            if state == state_local_computation:
                self.progress = 'computing...'
                data = random.randint(1, 6)
                print(f'[CLIENT] Sending roll ({data}) to master', flush=True)
                self.data_outgoing = json.dumps(data)
                self.status_available = True
                state = state_local_gather

            # GLOBAL PART

            if state == state_global_gather:
                self.progress = 'gathering...'
                if len(self.data_incoming) == len(self.clients) - 1:
                    state = state_global_computation

            if state == state_global_computation:
                self.progress = 'computing...'
                data = sum(self.data_incoming)
                print(f'[MASTER] Global sum is {data}', flush=True)
                self.data_outgoing = json.dumps(data)
                self.status_available = True
                state = state_finishing

            if state == state_finishing:
                self.progress = 'finishing...'
                time.sleep(10)
                self.status_finished = True
                break

            time.sleep(0.1)


logic = AppLogic()
