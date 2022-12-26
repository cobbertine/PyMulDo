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
            self.data = ""

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
            print("An unknown error has occurred, and the the creation of the directory has failed. Aborting program.")
            return

        worker_threads = list()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.total_threads) as executor:
            with open(self.url_list_file, "r") as url_list_file:
                for url in url_list_file:
                    url = url.strip()
                    worker_threads.append(executor.submit(self.get_url_resource, AbstractMultithreadRequester.WorkerObject(url)))

        for worker_thread in concurrent.futures.as_completed(worker_threads):
            worker_object = worker_thread.result()
            if worker_object.success is False:
                print(f"Worker accessing {worker_object.resource_name} has failed.")
                with open(os.path.join(self.OUTPUT_FOLDER_NAME,self.ERROR_LOG_FILE_NAME), "a") as error_log_file_pointer:
                    error_log_file_pointer.write(worker_object.url + "\n")
            else:
                print(f"Worker {worker_object.resource_name} has returned successfully.")
                self.process_finished_worker_data(worker_object)
        print("Job complete. Refer to console output for failed URLs.")

    def get_url_resource(self, worker_object):
        current_try = 0
        while current_try < self.total_retries:
            try:
                response_data = requests.get(worker_object.url, timeout=self.timeout)
                if response_data.status_code not in self.STATUS_CODE_CHECKER:
                    raise Exception
                else:
                    response_data = response_data.text
                worker_object.update_status(True, response_data)
                return worker_object
            except Exception:
                current_try = current_try + 1
                time.sleep(self.retry_wait_time_seconds)
        return worker_object        

    def write_data_to_disk(self, worker_object):
        with open(os.path.join(self.OUTPUT_FOLDER_NAME, worker_object.resource_name), "w") as worker_file_pointer:
            worker_file_pointer.write(worker_object.data)

    @abc.abstractmethod
    def process_finished_worker_data(self, worker_object):
        pass
