import concurrent.futures
import time
import abc
import requests
import os
import json
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AbstractMultithreadRequester(abc.ABC):
    """
    An abstract class that implements the functionality required to iterate over a list of URLs from a file and access the resource at each of those URLs.
    The class offers a variety of configuration options for multithreading and handling retries and wait times.
    The only unimplemented function in this class is "handle_successful_connection", leaving it to child classes to decide what should happen once a resource is retrieved.
    """    
    class ThreadDataObject:
        """
        A class that holds important information for each launched thread
        It tells the thread what URL it should access and it allows the thread to return the resource from that URL in the member field "data"
        """        
        def __init__(self, url):
            self.url = url
            try:
                self.resource_name = list(filter(len, url.split("/")))[-1]
            except Exception:
                print(f"Possibly malformed url: {url}")
                self.resource_name = url
            self.success = False
            self.data = None

    class StatusCodeChecker:
        """
        A class that holds what Status Codes the user has specified as OK
        If the user has not supplied any codes, then it is assumed that all codes are OK.
        """        
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

    def __init__(self, url_list_file, total_threads, total_retries, retry_wait_time_seconds, connection_timeout_seconds, status_code_whitelist, mode, skip_request_verification, configuration_file):
        def validate_configuration_file():
            while True:
                try:
                    self.REQUEST_FUNCTION("", **self.CONFIGURATION_OPTIONS)
                except TypeError as unknown_option_exception:
                    unknown_option = re.match(r"(^.+?got an unexpected keyword argument )(.+)", str(unknown_option_exception)).group(2).replace("'", "")
                    print(f"Warning! The option '{unknown_option}' is not recognised by the request function. Skipping...")
                    del self.CONFIGURATION_OPTIONS[unknown_option]
                except Exception:
                    return   

        self.URL_LIST_FILE = url_list_file
        self.TOTAL_THREADS = total_threads
        self.TOTAL_RETRIES = total_retries
        self.RETRY_WAIT_TIME_SECONDS = retry_wait_time_seconds
        self.CONNECTION_TIMEOUT_SECONDS = connection_timeout_seconds
        self.STATUS_CODE_CHECKER = AbstractMultithreadRequester.StatusCodeChecker(status_code_whitelist)         
        self.REQUEST_FUNCTION = requests.post if mode == "post" else requests.get
        self.SKIP_REQUEST_VERIFICATION = skip_request_verification

        if len(configuration_file) == 0:
            self.CONFIGURATION_OPTIONS = {}
        else:
            with open(configuration_file) as config_file_pointer:
                self.CONFIGURATION_OPTIONS = json.load(config_file_pointer)
            validate_configuration_file()
        print("Configuration options loaded...")

    def launch_threads(self):
        """
        This is essentially the entry function for this class, which initiates the retrieval process based on the user supplied program arguments.
        """        
        try:
            os.mkdir("output")
        except FileExistsError:
            pass
        except Exception:
            print("An unknown error has occurred, and the the creation of the output directory has failed. Aborting program.")
            return

        task_list = list()

        # Exiting this with block is equivalent to calling executor.shutdown(wait=True)
        # So "concurrent.futures.as_completed" must be inside this block
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.TOTAL_THREADS) as executor:
            with open(self.URL_LIST_FILE, "r") as url_list_file:
                for url in url_list_file:
                    url = url.strip()
                    if len(url) > 0:
                        task_list.append(executor.submit(self.run_url_thread, AbstractMultithreadRequester.ThreadDataObject(url)))

            print(f"All {len(task_list)} tasks are now queued.")
            self.await_threads(task_list)
            print("Job complete. Refer to console output for successful and unsuccessful URLs.")

    def await_threads(self, task_list):
        """
        This function is launched once all tasks are queued by the ThreadPoolExecutor.
        It will continously wait for a thread to complete its work and then process that thread appropriately.
        The function will return once all threads have finished their work and all of them have been processed.
        The success or failure of these threads is written to a log file.
        """        
        def write_outcome_to_log_file(file_name, outcome_text):
            with open(os.path.join(self.OUTPUT_FOLDER_NAME, file_name), "a") as log_file_pointer:
                log_file_pointer.write(outcome_text)  

        print("Waiting for threads to complete...")
        task_count = len(task_list)

        for encapsulated_thread_data_object in concurrent.futures.as_completed(task_list):
            thread_data_object = encapsulated_thread_data_object.result()
            if thread_data_object.success is True:
                print(f"Thread {thread_data_object.resource_name} has returned successfully.")
                write_outcome_to_log_file(self.SUCCESS_LOG_FILE_NAME, thread_data_object.url + "\n")
            else:
                print(f"Thread '{thread_data_object.resource_name}' has returned unsuccessfully.")
                write_outcome_to_log_file(self.ERROR_LOG_FILE_NAME, thread_data_object.url + "\n")
            task_count = task_count - 1
            print(f"Remaining tasks: {task_count}")

    def run_url_thread(self, thread_data_object):
        """
        The entry function for each thread as configured by ThreadPoolExecutor
        It will attempt to establish a connection to the specified URL and then handle that connection, with the behaviour of this process controlled by the user supplied program arguments and the implementation of "handle_successful_connection"
        """    
        if self.repeat_on_failure(self.get_url_resource, thread_data_object) == True:
            thread_data_object.success = self.handle_successful_connection(thread_data_object)
        # "data" is the result of a call to a request function where "stream=True" has been set. Therefore, unless the data object is consumed entirely, it is necessary to call the close function on it once work has been complete.
        if thread_data_object.data is not None:
            thread_data_object.data.close()
        return thread_data_object

    def get_url_resource(self, thread_data_object):
        response_data = self.REQUEST_FUNCTION(thread_data_object.url, timeout=self.CONNECTION_TIMEOUT_SECONDS, stream=True, verify=(not self.SKIP_REQUEST_VERIFICATION), **self.CONFIGURATION_OPTIONS)
        if response_data.status_code not in self.STATUS_CODE_CHECKER:
            return False
        thread_data_object.data = response_data
        return True    

    def repeat_on_failure(self, target_function, *target_function_arg_list, exception_type=Exception):
        """
        This function will attempt to run "target_function". If there is an error, it will wait for RETRY_WAIT_TIME_SECONDS and try again up to TOTAL_RETRIES, which is specified by the user supplied program arguments
        "target_function" must return True on success and it can either return False or raise an exception on failure.
        By default, this function wraps "target_function" in a general try ... except Exception block, but a different Exception type can be provided
        """        
        current_try = 0
        while current_try <= self.TOTAL_RETRIES:
            if current_try > 0:
                time.sleep(self.RETRY_WAIT_TIME_SECONDS)
            try:
                if target_function(*target_function_arg_list) == True:
                    return True
            except exception_type as exception_object:
                pass
            current_try = current_try + 1
        return False

    @abc.abstractmethod
    def handle_successful_connection(self, thread_data_object):
        """
        This is an abstract function which must be implemented by a child class. The child class implements this function to decide how a successful connection to a URL  should be handled
        It must return a boolean indicating success or failure
        """        
        pass
