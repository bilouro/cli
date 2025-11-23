import base64
import json
import requests
import logging
from enum import Enum


class Environment(Enum):
    DEV = "SYSTEM-DEV"
    QA = "SYSTEM-QA"
    TEST = "SYSTEM-TEST"
    PROD = "SYSTEM"


class Authenticator:
    def __init__(self, client_id: str, client_secret: str, environment: Environment):
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        self.token = None

    def url_suffix(self) -> str:
        if self.environment == Environment.PROD:
            return ""
        env_name = self.environment.value.replace('SYSTEM-', '').lower()
        return f"-{env_name}"

    def environment_realm(self) -> str:
        return self.environment.value

    def authenticate(self):
        url = f"https://SYSTEM-auth{self.url_suffix()}.COM/realms/{self.environment_realm()}/protocol/openid-connect/token"
        print(f"Authenticating with URL: {url}")
        response = self.request_post_data(url)

        if response.status_code == 200:
            response_data = json.loads(response.text)
            access_token = response_data.get('access_token', '')
            if access_token:
                self.token = f"Bearer {access_token}"
                print('Authenticated Successfully!')
                logging.info(f'Authenticated Successfully with token: {self.token}')
            else:
                error_msg = 'Access token not found in the response.'
                print(error_msg)
                logging.error(error_msg)
        elif response.status_code == 400:
            error_msg = 'Authentication failed: Status code 400'
            print(error_msg)
            logging.error(error_msg)
            raise Exception(error_msg)
        else:
            error_msg = f'Authentication failed: Status code {response.status_code}'
            print(error_msg)
            logging.error(error_msg)
            raise Exception(error_msg)

    def request_post_data(self, url):
        if not self.client_id or not self.client_secret:
            raise Exception("Client ID and Secret are not set")
        authorization = base64.b64encode(bytes(f"{self.client_id}:{self.client_secret}", "ISO-8859-1")).decode("ascii")
        headers = {"Authorization": f"Basic {authorization}", "Content-Type": "application/x-www-form-urlencoded"}
        body = {"grant_type": "client_credentials"}
        response = requests.post(url, data=body, headers=headers)
        return response
