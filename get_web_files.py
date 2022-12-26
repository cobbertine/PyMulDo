import abstract_multithread_requester

class GetWebFiles(abstract_multithread_requester.AbstractMultithreadRequester):
    def process_finished_worker_data(self, worker_object):
        self.write_data_to_disk(worker_object)