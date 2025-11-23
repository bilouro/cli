#!/usr/bin/env python3
import pandas as pd
import argparse
import sys

from systemclibase import SystemCliBase, ProgressBar


class SystemcliCreate(SystemCliBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.actual_columns = set()

    def validate_csv_columns(self, df):
        """
        Validate that all required columns exist in the CSV
        """
        self.actual_columns = set(df.columns)

        # Define required columns
        required_columns = [
            'client_fantasy_name', 'client_surname', 'client_firstname'
        ]

        print("Column validation:")
        print("-" * 40)

        missing_columns = []
        for col in required_columns:
            if col in self.actual_columns:
                print(f"✓ {col}")
            else:
                print(f"✗ {col} - MISSING")
                missing_columns.append(col)

        if missing_columns:
            print(f"\nERROR: Missing required columns: {missing_columns}")
            print("\nAvailable columns:")
            for col in sorted(self.actual_columns):
                if not col.startswith('Unnamed:'):
                    print(f"  - {col}")
            raise ValueError(f"Missing required columns: {missing_columns}")

        print("\nColumn validation passed!")
        return True

    def safe_get_value(self, row, column_name):
        """
        Safely get value from row, handling missing columns gracefully
        """
        if column_name in self.actual_columns:
            return self.get_value(row[column_name])
        else:
            return None

    def generate_example_csv(self):
        csv = """client_name;client_fantasy_name;client_surname"""

        with open(self.output_filename, 'w') as f:
            f.write(csv)
        print(f"Example CSV file generated: {self.output_filename}")

    def execute(self):
        lines = self.count_lines(self.input_filename)
        print(f"{lines -1} to be processed...\n")

        sample_df = pd.read_csv(self.input_filename, sep=';', header=0, index_col=False, nrows=1)
        print(f"Validating CSV structure...\n")
        self.validate_csv_columns(sample_df)

        progress_bar = ProgressBar(lines-1, length=35)

        first_iteration = True
        for chunk in pd.read_csv(self.input_filename, sep=';', header=0, index_col=False, chunksize=100):
            csv_rows = []

            for index, row in chunk.iterrows():
                try:
                
                    if self.create_client(csv_rows, row, index):
                        progress_bar.id_created()
                    else:
                        progress_bar.validation_error()

                except Exception as e:
                    print(f"Error processing row {index}: {e}")
                    csv_row = row.to_dict()
                    csv_row['result_status'] = 'error'
                    csv_row['error_message'] = str(e)
                    csv_rows.append(csv_row)
                    progress_bar.validation_error()

            df = pd.DataFrame(csv_rows)
            if first_iteration:
                first_iteration = False
                df.to_csv(self.output_filename, mode='w', sep=';', index=False)
            else:
                df.to_csv(self.output_filename, mode='a', sep=';', header=False, index=False)

        progress_bar.print_final_stats()

    def get_identifiers_safe(self, row, prefix):
        """
        Safely extract identifiers, handling missing columns
        """
        identifiers = []
        for i in range(3):  # Check up to 3 identifiers
            code_col = f"{prefix}[{i}].code"
            value_col = f"{prefix}[{i}].value"

            code = self.safe_get_value(row, code_col)
            value = self.safe_get_value(row, value_col)

            if code and value:
                identifiers.append({"code": code, "value": value})

        return identifiers

    def populate_create_json(self, row):

        json_data = {
            "client": {
                "firstname": first,
                "lastname": last
            }
        }
        return json_data

    def create_client(self, csv_rows, row, index):
        try:
            response = self.create_call(self.populate_create_json(row))
            if response.status_code in [200, 201]:
                csv_row = row.to_dict()
                csv_row['result_status'] = 'created'
                csv_row['id'] = response.json().get('id')
                csv_row['input_file_line'] = index+2
                csv_rows.append(csv_row)
                return True
            else:
                csv_row = row.to_dict()
                csv_row['result_status'] = 'error'
                csv_row['input_file_line'] = index+2
                error_detail = response.json().get('detail', response.text) if response.text else 'Unknown error'
                csv_row['error_message'] = error_detail
                csv_rows.append(csv_row)
                return False
        except Exception as e:
            csv_row = row.to_dict()
            csv_row['result_status'] = 'error'
            csv_row['input_file_line'] = index+2
            csv_row['error_message'] = str(e)
            csv_rows.append(csv_row)
            return False

    def create_call(self, json_data, intent=0):
        response = self.request_post_json(json_data, f"https://system-gateway{self.url_suffix}.com/system-client/clients")

        if response.status_code == 401 and intent == 0:
            self.auth_systemservice(self.username, self.password)
            return self.create_call(json_data, intent+1)

        return response

def main():
    epilog = (
        "    \n"
        "NAME\n"
        "       systemcli-create - SYSTEM Command Line Interface for Create Client\n\n"
        "SYNOPSIS\n"
        "       systemcli-create [options]\n\n"
        "DESCRIPTION\n"
        "       systemcli-create is a command-line tool to create Clients in SYSTEM.\n"
        "       This tool provides a convenient way to batch create s via a CSV file.\n"
        "       The tool takes a CSV file as input and generates an output file with the results.\n\n"
        "OPTIONS\n"
        "       systemcli-create accepts the following command-line arguments:\n\n"
        "       -h, --help\n"
        "           Show this help message and exit.\n\n"
        "       -e \n"
        "           Generate an example CSV file. \n"
        "           This option can be used only with -o.\n\n"
        "       -i input_filename\n"
        "           Input file for the operation.\n\n"
        "       -o output_filename\n"
        "           Output file to be generated (will be overwritten if it already exists).\n\n"
        "       -u username\n"
        "           Username to connect to the SYSTEM API.\n\n"
        "       -p password\n"
        "           Password to connect to the SYSTEM API.\n\n"
        "       -env environment\n"
        "           Specify the environment to be used; options include 'prod', 'test' (default), 'qa',  and 'dev'.\n\n"
        "USAGE EXAMPLE\n"
        "       Generating an example CSV file\n"
        "       ./systemclicreate.py -e -o template.csv\n\n"
        "       Creating  in Test environment\n"
        "       ./systemclicreate.py -i input_file.csv -o result.csv -u USER -p PASS -env test\n"
        "    \n"
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
    parser.add_argument("-u", dest="username", help=argparse.SUPPRESS)
    parser.add_argument("-p", dest="password", help=argparse.SUPPRESS)
    parser.add_argument("-env", dest="environment", default='test', choices=['prod', 'test', 'qa', 'dev'],
                        help=argparse.SUPPRESS)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.generate_example:
        if args.input_filename or args.username or args.password or not args.output_filename:
            parser.error("-e must be used only with -o")
        with SystemcliCreate(output_filename=args.output_filename) as app:
            app.generate_example_csv()
    else:
        if not all([args.input_filename, args.output_filename, args.username, args.password]):
            parser.error("-u, -p, -i, and -o must be specified. (-env is optional)")
        with SystemcliCreate(username=args.username, password=args.password, input_filename=args.input_filename,
                            output_filename=args.output_filename, environment=args.environment) as app:
            app.execute()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
