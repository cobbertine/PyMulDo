import argparse
import get_web_files

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("url_list_file")
arg_parser.add_argument("total_threads", type=int)
arg_parser.add_argument("total_retries", type=int)
arg_parser.add_argument("retry_wait_time_seconds", type=int)
arg_parser.add_argument("timeout", type=int)
arg_parser.add_argument("--scw", metavar="status_code_whitelist", type=str, help="A list of status codes separated by a comma e.g. \"200,404\". If all codes are allowed, do not use this option", default="")

args = arg_parser.parse_args()
arg_list = [args.url_list_file, args.total_threads, args.total_retries, args.retry_wait_time_seconds, args.timeout, args.scw]

# Create object and launch e.g.
# get_web_files_object = get_web_files.GetWebFiles(*arg_list)
# get_web_files_object.launch_workers()
# or any other class you define...


get_web_files_object = get_web_files.GetWebFiles(*arg_list)
get_web_files_object.launch_workers()
