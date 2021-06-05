import configparser
import requests
import json
import secrets
import urllib.parse as urlparse
from urllib.parse import parse_qs
from bs4 import BeautifulSoup
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

login_url = config.get("url", "login")
identity_url = config.get("url", "identity")


class Tokens:

    def __init__(self):
        self.tokens = {}
        self.load_tokens_from_file()

    def get_access_token(self):
        if "accessToken" not in self.tokens:
            self.load_tokens_from_web()
        return self.tokens["accessToken"]

    def get_refresh_token(self):
        if "refreshToken" not in self.tokens:
            raise Exception("refreshToken not found")
        return self.tokens["refreshToken"]

    def load_tokens_from_file(self):
        token_file = config.get("settings", "token_file")
        path = Path(token_file)
        if path.is_file():
            logging.info("Retrieving tokens from file: %s", token_file)
            with open(token_file) as f:
                self.tokens = json.load(f)

    def load_tokens_from_web(self):
        logging.info("Retrieving tokens using web api")

        # using a session so that cookies are managed
        s = requests.Session()

        # fetch the login page
        params = {
            "nonce": secrets.token_urlsafe(12),
            "redirect_uri": "weconnect://authenticated"
        }
        logging.info("Fetching login page")
        resp = s.get(login_url + "/authorize", params=params)
        resp.raise_for_status()

        # submit email identity
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", { "id": "emailPasswordForm" })
        params = {}
        form_inputs = form.find_all("input")
        for form_input in form_inputs:
            params[form_input.get("name")] = form_input.get("value")
        params["email"] = config.get("user", "email")
        params["registerFlow"] = False
        logging.info("Submitting email as identity")
        resp = s.get(identity_url + form.get("action"), params=params)
        resp.raise_for_status()

        # submit password
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", { "id": "credentialsForm" })
        action = form.get("action").replace("/authenticate", "/phone-email/authenticate")
        data = {}
        form_inputs = form.find_all("input")
        for form_input in form_inputs:
            data[form_input.get("name")] = form_input.get("value")
        data["password"] = config.get("user", "password")

        # NOTE: shortcut alert! rather than define an endpoint
        # to service the authenticated callback we will just
        # capture the exception of which its message will include
        # the location with fragment containing the data we need
        try:
            logging.info("Submitting password")
            resp = s.post(identity_url + action, data=data)

            # sometimes updated terms-and-conditions need to be accepted
            soup = BeautifulSoup(resp.text, "html.parser")
            form = soup.find("form", { "id": "emailPasswordForm" })
            action = form.get("action")
            data = {}
            form_inputs = form.find_all("input")
            for form_input in form_inputs:
                data[form_input.get("name")] = form_input.get("value")
            logging.info("Accepting updated terms-and-conditions")
            resp = s.post(identity_url + action, data=data)

            # TODO: raise error as we should not reach here
            logging.error("Unexpected stage within the login process")
            logging.info("resp.status_code: %s", resp.status_code)
            logging.info("resp.text: %s", resp.text)
        except requests.exceptions.InvalidSchema as e:
            # No connection adapters were found for 'weconnect://authenticated#
            eMsg = str(e)
            location = eMsg[eMsg.index("weconnect"):-1]
            fragments = parse_qs(urlparse.urlparse(location).fragment)

        # fetch access and refresh tokens
        headers = { "Content-type": "application/json" }
        data = {
            "state": fragments["state"][0],
            "id_token": fragments["id_token"][0],
            "redirect_uri": "weconnect://authenticated",
            "region": "emea",
            "access_token": fragments["access_token"][0],
            "authorizationCode": fragments["code"][0]
        }
        logging.info("Fetching access and refresh tokens")
        resp = s.post(login_url + "/login/v1", headers=headers, json=data)
        resp.raise_for_status()

        # store access and refresh tokens in a file
        self.tokens = resp.json()
        with open(config.get("settings", "token_file"), "w") as f:
            json.dump(self.tokens, f)


    def refresh_tokens_from_web(self):
        logging.info("Refreshing tokens using web api")
        headers = {
            "Content-type": "application/json",
            "Authorization": "Bearer {}".format(self.get_refresh_token())
        }
        logging.info("Fetching new access and new refresh tokens")
        resp = requests.get(login_url + "/refresh/v1", headers=headers)
        resp.raise_for_status()

        # store access and refresh tokens in a file
        self.tokens = resp.json()
        with open(config.get("settings", "token_file"), "w") as f:
            json.dump(self.tokens, f)
