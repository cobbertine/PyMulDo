import os
import abstract_multithread_requester

class GetWebFiles(abstract_multithread_requester.AbstractMultithreadRequester):
    def write_all_data_to_disk(self, thread_data_object):
        with open(os.path.join(self.OUTPUT_FOLDER_NAME, thread_data_object.resource_name), "ab") as thread_data_file_pointer:
            for chunk in thread_data_object.data.iter_content(chunk_size=128):
                thread_data_file_pointer.write(chunk)
        return True
        
    def handle_successful_connection(self, thread_data_object):
        return self.run_retriable_task(self.write_all_data_to_disk, thread_data_object)