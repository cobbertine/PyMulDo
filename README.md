# PyMulDo - Python Multi-Downloader

## Requirements
This was developed with Python 3.10.7

## Client-side setup

### Python standard
* Open up a terminal and clone the repo
* Change to the repo's folder
* Type "pip install -r requirements.txt" (Some users may need to use "pip3" instead of "pip")
* Run main.py using the information in the **Usage** section

### Python virtual environment
* Open up a terminal and clone the repo
* Change to the repo's folder
* Type "pip install pipenv" (Some users may need to use "pip3" instead of "pip")
* Type "python3 -m pipenv install --ignore-pipfile"
* After successful installation, type "python3 -m pipenv shell"
* Run main.py using the information in the **Usage** section

## Usage

### Arguments

```
usage: main.py [-h] [-t total_threads] [-r total_retries] [-w retry_wait_time_seconds] [-c connection_timeout_seconds] [-s status_code_whitelist] [-m request_mode] [-d] [-f config_json_file] url_list_file


positional arguments:
  url_list_file         Specifies a file containing a list of URLs for this program to access.

options:
  -h, --help            show this help message and exit
  -t total_threads      Specifies how many threads can run concurrently. Default: 1
  -r total_retries      Specifies how many times a thread should attempt to access a URL after a failure before giving up. (A common failure case is a timeout). Default: 1
  -w retry_wait_time_seconds
                        Specifies (in seconds) how long a thread should wait after a failure before trying to access a URL again. NOTE: This is only applicable if 'total_retries' is > 0. Default: 3
  -c connection_timeout_seconds
                        Specifies (in seconds) how long a thread should wait for a response from a URL before aborting. Behaviour after aborting is dependent on 'total_retries' and 'retry_wait_time_seconds'.
                        Default: 3
  -s status_code_whitelist
                        Specifies a list of status codes separated by a comma e.g. "200,404" that indicate the thread has successfully accessed the URL. If all codes are allowed, do not use this option.
  -m request_mode       Specifies if the request will be a GET or a POST. Valid options: get|post. An invalid option will use the default value. Default: get
  -d                    This switch will indicate to the program to disable the request's server verification feature. If the default verify=True behaviour is wanted, do not use this option.
  -f config_json_file   Specifies a JSON configuration file containing extra options to pass into the request function. If none of the extra options defined in the file are needed, do not use this option.
```

### Launching

Launch examples:

```
# Using 20 threads, connect to the URLs in the provided list, and filter out connections that do not respond with "200 OK"
python3 main.py url_list.txt -t 20 -s 200 
```

### Output

Downloaded files and success and error logs are outputted to the "output" directory in the working directory