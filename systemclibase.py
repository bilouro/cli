import json
import pandas as pd
import requests as requests
import time
import sys
from colorama import Fore, init


class SystemCliBase:

    def str_to_bool(self, value):
        if isinstance(value, str):
            value = value.strip().lower()
            return value in ["true", "y", "yes"]
        elif isinstance(value, bool):
            return value
        else:
            return False

    def get_value(self, value):
        if pd.isna(value) or value == '':
            return None
        return value

    def get_identifiers(self, row, base_key):
        identifiers = []
        for i in range(3):
            key_code = f"{base_key}[{i}].code"
            key_value = f"{base_key}[{i}].value"

            if key_code in row and key_value in row:
                if pd.notna(row[key_code]) and pd.notna(row[key_value]):
                    identifiers.append({
                        "code": self.get_value(row[key_code]),
                        "value": self.get_value(row[key_value])
                    })
        return identifiers

    def __init__(self, username=None, password=None, input_filename=None, output_filename=None, environment='test',
                 lookup_only=False):
        self.username = username
        self.password = password
        self.input_filename = input_filename
        self.output_filename = output_filename
        self.token = None
        self.environment = environment
        environment_url_suffixes = {
            'prod': '',
            'test': '-test',
            'qa': '-qa',
            'dev': '-dev'
        }
        self.url_suffix = environment_url_suffixes[self.environment]
        self.lookup_only = lookup_only
        print('Starting...')

    def __enter__(self):
        if self.username and self.password:
            self.auth_systemservice(self.username, self.password)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def auth_systemservice(self, username, password):
        url = f"https://system-service{self.url_suffix}.com/system/rest/v2/login"
        data = {
            "user": username,
            "password": password
        }
        response = self.request_post_data(json.dumps(data), url)

        if response.status_code == 200:
            self.token = response.text
            print('Authenticated Successfully!')
        else:
            try:
                detail = response.json().get('detail', 'No detail provided')
            except ValueError:  # se ocorrer um erro ao decodificar o JSON
                detail = 'No detail provided'

            raise Exception(f"Failed to authenticate. Status code: {response.status_code}, Detail: {detail}")

    def request_post_json(self, json_data, url):
        headers = {
            "accept": "application/json",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=json_data)
        return response

    def request_post_data(self, json_data, url):
        headers = {
            "accept": "application/json",
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, data=json_data)
        return response

    def generate_example_csv(self):
        pass

    def execute(self):
        pass

    def count_lines(self, filepath):
        def count_generator(reader):
            b = reader(1024 * 1024)
            while b:
                yield b
                b = reader(1024 * 1024)

        with open(filepath, 'rb') as fp:
            c_generator = count_generator(fp.raw.read)
            count = sum(buffer.count(b'\n') for buffer in c_generator)
        return count + 1


class ProgressBar:

    def __init__(self, total, length=50):
        init(autoreset=True)
        self.start_time = time.time()
        self.total = total
        self.length = length
        self.totals = [0, 0, 0, total]

    def format_time(self, total_seconds):
        if total_seconds < 60:
            time_str = f"{total_seconds:.0f}s"
        elif total_seconds < 3600:
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            time_str = f"{minutes}m {seconds}s"
        elif total_seconds < 86400:
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            time_str = f"{hours}h {minutes}m"
        else:
            days = int(total_seconds // 86400)
            hours = int((total_seconds % 86400) // 3600)
            time_str = f"{days}d {hours}h"
        return time_str

    def progress_bar(self):
        filled_length = sum(self.totals) - self.totals[-1]

        bars = [
            Fore.GREEN + '█' * int(self.length * self.totals[0] // self.total),
            Fore.RED + '█' * int(self.length * self.totals[1] // self.total),
            Fore.YELLOW + '█' * int(self.length * self.totals[2] // self.total),
            Fore.LIGHTBLACK_EX + '-' * int(self.length * self.totals[3] // self.total),
        ]

        bar = ''.join(bars)
        bar += '-' * (self.length - len(bar))

        elapsed_time = time.time() - self.start_time
        estimated_time_left = elapsed_time / (filled_length if filled_length != 0 else 1) * self.totals[-1]
        time_left_str = self.format_time(estimated_time_left)

        self.legend = [
            Fore.GREEN + f'Entities Processed: {self.totals[0]}',
            Fore.RED + f'Validation Error: {self.totals[1]}',
            Fore.YELLOW + f'Suggestions Found: {self.totals[2]}',
            Fore.LIGHTBLACK_EX + f'Remaining: {self.totals[3]}',
            Fore.WHITE + f'Time Left: {time_left_str}',
        ]

        sys.stdout.write('\r|{}| {} {}\r'.format(bar, ' '.join(self.legend), ' ' * 10))
        sys.stdout.flush()

        return self.legend[:-2]  # Retiramos Remaining e Time Left

    def print_final_stats(self):
        elapsed_time = time.time() - self.start_time
        sys.stdout.write("\n\n")
        for stat in self.legend:
            sys.stdout.write(stat + "\n")
        sys.stdout.write(Fore.WHITE + "Total time elapsed: {}\n\n".format(self.format_time(elapsed_time)))

    def id_created(self):
        _totals = [1, 0, 0]
        self.update_totals(_totals)

    def validation_error(self):
        _totals = [0, 1, 0]
        self.update_totals(_totals)

    def suggestion_found(self):
        _totals = [0, 0, 1]
        self.update_totals(_totals)

    def update_totals(self, updates):
        for i, update in enumerate(updates):
            self.totals[i] += update
        self.totals[-1] -= sum(updates)
        self.legend = self.progress_bar()
