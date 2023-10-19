import configparser
import re
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

user_agent = config.get("url", "user_agent")
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
        headers = {
            "User-Agent": user_agent
        }
        params = {
            "nonce": secrets.token_urlsafe(12),
            "redirect_uri": "weconnect://authenticated"
        }
        logging.info("Fetching login page")
        resp = s.get(login_url + "/authorize", headers=headers, params=params)
        resp.raise_for_status()

        # submit email identity
        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form", {"id": "emailPasswordForm"})
        data = {}
        form_inputs = form.find_all("input")
        for form_input in form_inputs:
            data[form_input.get("name")] = form_input.get("value")
        data["email"] = config.get("user", "email")
        data["registerFlow"] = False
        logging.info("Submitting email as identity")
        form_url = identity_url + form.get("action")
        resp = s.post(form_url, data=data)
        resp.raise_for_status()

        # submit password
        soup = BeautifulSoup(resp.text, "html.parser")
        form_url = form_url.replace("/login/identifier", "/login/authenticate")
        data["password"] = config.get("user", "password")

        hmac = None
        script_elements = soup.find_all("script")
        for script_element in script_elements:
            if script_element.string:
                if script_element.string.strip().startswith("window._IDK ="):
                    m = re.search(r'\"hmac\":\"([^\"]*)\"', script_element.string)
                    if m:
                        hmac = m.group(1)
        if not hmac:
            logging.error("Unable to locate hmac")
        data["hmac"] = hmac

        # NOTE: shortcut alert! rather than define an endpoint
        # to service the authenticated callback we will just
        # capture the exception of which its message will include
        # the location with fragment containing the data we need
        try:
            logging.info("Submitting password")
            resp = s.post(form_url, data=data)

            # if we get here instead of catching an exception it means
            # that there are updated terms-and-conditions that need to
            # be accepted
            soup = BeautifulSoup(resp.text, "html.parser")
            logging.info(resp.text)

            # TODO: support new terms-and-conditions flow
            #       for now, login via app or https://vwid.vwgroup.io/account
            #       and accept the new terms-and-conditions

            # TODO: raise error as we should not reach here
            logging.error("Unexpected stage within the login process")
            logging.info("resp.text: %s", resp.text)
        except requests.exceptions.InvalidSchema as e:
            # No connection adapters were found for 'weconnect://authenticated#
            e_msg = str(e)
            location = e_msg[e_msg.index("weconnect"):-1]
            fragments = parse_qs(urlparse.urlparse(location).fragment)

        # fetch access and refresh tokens
        headers = {
            "User-Agent": user_agent,
            "Content-type": "application/json"
        }
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
            "User-Agent": user_agent,
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
