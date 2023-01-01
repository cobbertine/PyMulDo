import concurrent.futures
import time
import abc
import requests
import os

class AbstractMultithreadRequester(abc.ABC):
    class WorkerObject:
        def __init__(self, url):
            self.url = url
            self.resource_name = url.split("/")[-1]
            self.success = False
            self.data = None

        def update_status(self, success, data):
            self.success = success
            self.data = data

    class StatusCodeChecker:
        def __init__(self, status_code_whitelist):
            self.status_code_whitelist = set(map(int, filter(len, status_code_whitelist.split(","))))
            self.is_all_codes_allowed = len(self.status_code_whitelist) == 0
        def __contains__(self, key):
            if self.is_all_codes_allowed:
                return True
            else:
                return key in self.status_code_whitelist

    OUTPUT_FOLDER_NAME = "output"
    SUCCESS_LOG_FILE_NAME = "success_log.txt"
    ERROR_LOG_FILE_NAME = "error_log.txt"
    STATUS_CODE_CHECKER = None

    def __init__(self, url_list_file, total_threads, total_retries, retry_wait_time_seconds, timeout, status_code_whitelist):
        self.url_list_file = url_list_file
        self.total_threads = total_threads
        self.total_retries = total_retries
        self.retry_wait_time_seconds = retry_wait_time_seconds
        self.timeout = timeout
        self.STATUS_CODE_CHECKER = AbstractMultithreadRequester.StatusCodeChecker(status_code_whitelist)         

    def launch_workers(self):
        try:
            os.mkdir("output")
        except FileExistsError:
            pass
        except Exception:
            print("An unknown error has occurred, and the the creation of the output directory has failed. Aborting program.")
            return

        worker_threads = list()

        # Exiting this with block is equivalent to calling executor.shutdown(wait=True)
        # So "concurrent.futures.as_completed" must be inside this block
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.total_threads) as executor:
            with open(self.url_list_file, "r") as url_list_file:
                for url in url_list_file:
                    url = url.strip()
                    worker_threads.append(executor.submit(self.get_url_resource, AbstractMultithreadRequester.WorkerObject(url)))

            print(f"All {len(worker_threads)} tasks are now queued.")
            self.await_workers(worker_threads)
            print("Job complete. Refer to console output for successful and unsuccessful URLs.")

    def await_workers(self, worker_threads):
        def write_outcome_to_log_file(file_name, outcome_text):
            with open(os.path.join(self.OUTPUT_FOLDER_NAME, file_name), "a") as log_file_pointer:
                log_file_pointer.write(outcome_text)  

        print("Waiting for threads to complete...")
        worker_count = len(worker_threads)

        for worker_thread in concurrent.futures.as_completed(worker_threads):
            worker_object = worker_thread.result()
            if worker_object.success is True:
                print(f"Worker {worker_object.resource_name} has returned successfully.")
                print(f"Attempting to process results of worker '{worker_object.resource_name}'...")
                if self.process_finished_worker_data(worker_object) == True:
                    print(f"Worker '{worker_object.resource_name}' has been processed successfully.")
                    write_outcome_to_log_file(self.SUCCESS_LOG_FILE_NAME, worker_object.url + "\n")
                else:
                    print(f"Worker '{worker_object.resource_name}' has been processed unsuccessfully.")
                    write_outcome_to_log_file(self.ERROR_LOG_FILE_NAME, worker_object.url + "\n")
            else:
                print(f"Worker '{worker_object.resource_name}' has returned unsuccessfully.")
                write_outcome_to_log_file(self.ERROR_LOG_FILE_NAME, worker_object.url + "\n")
            worker_count = worker_count - 1
            print(f"Remaining workers: {worker_count}")

    def get_url_resource(self, worker_object):
        def f():
            print(f"!TEST! Worker '{worker_object.resource_name}' getting url")
            response_data = requests.get(worker_object.url, timeout=self.timeout, stream=True)
            if response_data.status_code not in self.STATUS_CODE_CHECKER:
                raise Exception
            worker_object.update_status(True, response_data)
            return True    
        self.run_retriable_task(f, [])
        return worker_object

    def write_data_to_disk(self, worker_object):
        def f():
            print(f"!TEST! Worker '{worker_object.resource_name}' writing data")
            with open(os.path.join(self.OUTPUT_FOLDER_NAME, worker_object.resource_name), "wb") as worker_file_pointer:
                for chunk in worker_object.data.iter_content(chunk_size=128):
                    worker_file_pointer.write(chunk)
            return True
        return self.run_retriable_task(f, [])            

    # Target function must return True when it has successfully completed.
    def run_retriable_task(self, target_function, target_function_arg_list):
        current_try = 0
        while current_try < self.total_retries:
            try:
                if target_function(*target_function_arg_list) == True:
                    return True
            except Exception:
                current_try = current_try + 1
                time.sleep(self.retry_wait_time_seconds)
        return False

    @abc.abstractmethod
    def process_finished_worker_data(self, worker_object):
        pass
