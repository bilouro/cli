# SYSTEM Command Line Tools

## Overview

The SYSTEM CLI is a suite of utilities designed to streamline interactions with the SYSTEM through a command line interface.
It allows for batch operations such as bulk creation via CSV files.

## Setting Up the Environment

To set up the development environment, follow the steps outlined below:

1. Ensure Python 3.x is installed on your system. You can download it from the [official Python website](https://www.python.org/).

2. Clone the repository to your local machine 

3. Navigate to the project directory:
   ```
   cd system-cli
   ```

4. Create a virtual environment in the project directory with the command:
   - **On Windows:**
     ```
     python3 -m venv .venv
     ```
   - **On Unix or MacOS:**
     ```
     python3 -m venv ./venv
     ```


5. Activate the virtual environment:
   - **On Windows:**
     ```
     .venv\Scripts\activate
     ```
   - **On Unix or MacOS:**
     ```
     source venv/bin/activate
     ```

6. Install the required Python packages using the following command:
   ```
   pip install -r requirements.txt
   ```

## Usage

To use the SYSTEM command line tools, refer to the built-in help system which provides an overview of available options and their functionalities:
- [systemcli-createclient](manuals/createclient.md)

A typical workflow includes the following steps:

1. Generate an example CSV file with the necessary command.
2. Populate the CSV file with the appropriate data.
3. Execute the tool with the required parameters.
4. Check results in output_file. 

