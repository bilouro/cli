#!/usr/bin/env python3
import pandas as pd
import argparse
import sys
import requests

from Authenticator import Authenticator, Environment
from systemclibase import ProgressBar


def _map_environment(env_str):
    env_mapping = {
        'dev': Environment.DEV,
        'qa': Environment.QA,
        'test': Environment.TEST,
        'prod': Environment.PROD
    }
    return env_mapping.get(env_str.lower(), Environment.TEST)


class SystemCliAddIdentifier:
    def __init__(self, client_id=None, client_secret=None, input_filename=None,
                 output_filename=None, environment='test'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.input_filename = input_filename
        self.output_filename = output_filename
        self.environment = _map_environment(environment)
        self.authenticator = None if not (client_id and client_secret) else \
            Authenticator(client_id, client_secret, self.environment)

    def __enter__(self):
        if self.authenticator:
            self.authenticator.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # sonarlint requires a comment here
        pass

    def generate_example_excel(self):
        data = {
            'id': [1234],
            'code': ['XPTO'],
            'value': ['COD-for-XPTO'],
        }
        df = pd.DataFrame(data)
        df.to_csv(self.output_filename, index=False)
        print(f"Example Excel file generated: {self.output_filename}")

    def execute(self):
        print("Starting...")
        df = pd.read_csv(self.input_filename, delimiter=';')
        total_rows = len(df)
        print(f"{total_rows} identifiers to be processed...")
        print()
        progress_bar = ProgressBar(total_rows, length=35)

        results = []
        for index, row in df.iterrows():
            id = row['id'.upper()]
            identifier_data = {
                "code": row['code'.upper()],
                "value": row['value'.upper()]
            }
            response = self.add_identifier_call(id, identifier_data)
            result_row = row.to_dict()
            result_row['input_file_line'] = index + 2

            if response.status_code == 201:
                result_row['result_status'] = 'created'
                result_row.update(response.json())
                progress_bar.id_created()
            else:
                result_row['result_status'] = 'error'
                result_row['error_message'] = response.text
                print(f"Error processing ID {id} at line {index + 2}: {response.text}")
                progress_bar.validation_error()
            results.append(result_row)
            # Checkpoint: Save the intermediate results every 100 records
            if (index + 1) % 100 == 0:
                pd.DataFrame(results).to_csv(self.output_filename, index=False)
                print(f"Checkpoint: Saved progress at {index + 1} records.")

        result_df = pd.DataFrame(results)
        result_df.to_csv(self.output_filename, index=False)
        progress_bar.print_final_stats()

    def add_identifier_call(self, id, identifier_data, attempt=0):
        url_suffix = self.authenticator.url_suffix() if self.authenticator.environment != Environment.PROD else ""
        url = f"\nhttps://system-gateway{url_suffix}.com/system-client/clients/{id}/identifiers"
        headers = {"Authorization": self.authenticator.token, "Content-Type": "application/json"}
        #print(f"\nURL: {url}")
        try:
            response = requests.post(url, json=identifier_data, headers=headers)

            if response.status_code == 401 and attempt == 0:
                self.authenticator.authenticate()
                return self.add_identifier_call(id, identifier_data, attempt + 1)
            return response

        except requests.exceptions.RequestException as e:
            class ErrorResponse:
                def __init__(self, status_code, text):
                    self.status_code = status_code
                    self.text = text

                def json(self):
                    return {"error": self.text}

            return ErrorResponse(500, str(e))


def main():
    epilog = (
        "NAME\n"
        "       systemcli-addidentifier - SYSTEM Command Line Interface for Adding Identifiers\n\n"
        "SYNOPSIS\n"
        "       systemcli-addidentifier [options]\n\n"
        "DESCRIPTION\n"
        "       systemcli-addidentifier is a command-line tool to add identifiers in SYSTEM.\n"
        "       This tool provides a convenient way to batch add identifiers via an Excel file.\n"
        "       The tool takes an Excel file as input and generates an output file with the results.\n\n"
        "OPTIONS\n"
        "       -h, --help\n"
        "           Show this help message and exit.\n\n"
        "       -e \n"
        "           Generate an example Excel file. \n"
        "           This option can be used only with -o.\n\n"
        "       -i input_filename\n"
        "           Input Excel file for the operation.\n\n"
        "       -o output_filename\n"
        "           Output Excel file to be generated (will be overwritten if it already exists).\n\n"
        "       --client-id client_id\n"
        "           Client ID for authentication.\n\n"
        "       --client-secret client_secret\n"
        "           Client Secret for authentication.\n\n"
        "       -env environment\n"
        "Specify the environment to be used; options include 'prod', 'test' (default), 'qa', and 'dev'.\n\n"
        "USAGE EXAMPLE\n"
        "       Generating an example Excel file\n"
        "       ./systemcliaddidentifier.py -e -o template.xlsx\n\n"
        "       Adding identifiers in Test environment\n"
        "./systemcliaddidentifier.py -i input_file.xlsx -o result.xlsx --client-id CLIENT_ID --client-secret "
        "CLIENT_SECRET -env test\n"
    )
    parser = argparse.ArgumentParser(
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    parser.add_argument("-e", dest="generate_example", action='store_true', help=argparse.SUPPRESS)
    parser.add_argument("-i", dest="input_filename", help=argparse.SUPPRESS)
    parser.add_argument("-o", dest="output_filename", help=argparse.SUPPRESS)

    group_id = parser.add_mutually_exclusive_group()
    group_id.add_argument("-u", dest="client_id", help=argparse.SUPPRESS)
    group_id.add_argument("--client-id", dest="client_id", help=argparse.SUPPRESS)

    group_secret = parser.add_mutually_exclusive_group()
    group_secret.add_argument("-p", dest="client_secret", help=argparse.SUPPRESS)
    group_secret.add_argument("--client-secret", dest="client_secret", help=argparse.SUPPRESS)

    parser.add_argument("-env", dest="environment", default='test',
                        choices=['prod', 'test', 'qa', 'dev'],
                        help=argparse.SUPPRESS)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.generate_example:
        if args.input_filename or args.client_id or args.client_secret or not args.output_filename:
            parser.error("-e must be used only with -o")
        with SystemCliAddIdentifier(output_filename=args.output_filename) as app:
            app.generate_example_excel()
    else:
        if not all([args.input_filename, args.output_filename, args.client_id, args.client_secret]):
            parser.error("Client ID (-u or --client-id), Client Secret (-p or --client-secret), -i, and -o must be "
                         "specified. (-env is optional)")
        with SystemCliAddIdentifier(
                client_id=args.client_id,
                client_secret=args.client_secret,
                input_filename=args.input_filename,
                output_filename=args.output_filename,
                environment=args.environment
        ) as app:
            app.execute()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)

# generate example csv
# ./systemcliaddidentifier.py -e -o template.xlsx

# execute script
# ./systemcliaddidentifier.py -i INPUT.xlsx -o OUTPUT.xlsx --client-id ID --client-secret SECRET -env ENVIRONMENT

