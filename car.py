import configparser
import datetime
import requests
import json
import time
from tokens import Tokens
import logging

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

api_url = config.get("url", "api")


class Car:

    def __init__(self):
        self.tokens = Tokens()

    def get_vehicles(self):
        logging.info("Fetching vehicles")
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self.tokens.get_access_token())
        }
        resp = self._get(api_url + "/vehicles", headers=headers)
        resp_json = resp.json()

        # store vehicles in a file
        filename = time.strftime(config.get("settings", "vehicles_file"))
        with open(filename, "w") as f:
            json.dump(resp_json, f, sort_keys=True, indent=4)

        if resp_json["data"]:
            for d in resp_json["data"]:
                logging.info("model        : %s", d["model"])
                logging.info("    nickname : %s", d["nickname"])
                logging.info("    role     : %s", d["role"])
                logging.info("    vin      : %s", d["vin"])

    def get_status(self):
        logging.info("Fetching vehicle status")
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(self.tokens.get_access_token())
        }
        vin = config.get("car", "vin")
        resp = self._get(api_url + "/vehicles/" + vin + "/selectivestatus?jobs=all", headers=headers)
        resp_json = resp.json()

        resp_json["requestTimestamp"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # store status in a file
        filename = time.strftime(config.get("settings", "vehicle_status_file"))
        with open(filename, "w") as f:
            json.dump(resp_json, f, sort_keys=True, indent=4)

        if resp_json["charging"]:
            plug_connection_state = resp_json["charging"]["plugStatus"]["value"]["plugConnectionState"]
            charging_state = resp_json["charging"]["chargingStatus"]["value"]["chargingState"]
            current_soc = resp_json["charging"]["batteryStatus"]["value"]["currentSOC_pct"]
            battery_status_timestamp = resp_json["charging"]["batteryStatus"]["value"]["carCapturedTimestamp"]

            remaining_mins = resp_json.get("charging", {}).\
                get("chargingStatus", {}).\
                get("value", {}).\
                get("remainingChargingTimeToComplete_min", None)

            time_left = "??? remaining"
            if remaining_mins is not None:
                r_hour, r_min = divmod(remaining_mins, 60)
                time_left = "{}h {}m remaining".format(r_hour, r_min)

            charging_info = "{}, {} kW {}, {}".format(
                resp_json["charging"]["chargingStatus"]["value"]["chargeMode"],
                resp_json["charging"]["chargingStatus"]["value"]["chargePower_kW"],
                resp_json["charging"]["chargingStatus"]["value"]["chargeType"],
                time_left
            )
            logging.info("plug_connection_state    : %s", plug_connection_state)
            logging.info("charging_state           : {} ({})".format(charging_state, charging_info))
            logging.info("current_soc              : %s%%", current_soc)
            logging.info("battery_status_timestamp : %s", battery_status_timestamp)

        return resp_json

    # action = start | stop
    def set_charging(self, action="start"):
        resp_json = self.get_status()

        if not resp_json["charging"]:
            logging.error("Unable to determine current connection and charging status")
            return

        plug_connection_state = resp_json["charging"]["plugStatus"]["value"]["plugConnectionState"]
        charging_state = resp_json["charging"]["chargingStatus"]["value"]["chargingState"]

        if not plug_connection_state == "connected":
            logging.warn("Plug needs to be connected - currently: %s", plug_connection_state)
            return
        if action == "start" and charging_state == "charging":
            logging.info("Currently charging - nothing more to do")
            return
        if action == "stop" and not charging_state == "charging":
            logging.info("Not currently charging - nothing more to do")
            return

        logging.info("Requesting vehicle to %s charging", action)

        headers = {
            "Content-type": "application/json",
            "Content-version": "1",
            "Accept": "*/*",
            "Authorization": "Bearer {}".format(self.tokens.get_access_token())
        }
        vin = config.get("car", "vin")
        resp = self._post(api_url + "/vehicles/" + vin + "/charging/" + action, headers=headers)
        resp_json = resp.json()
        logging.info("requestID: %s", resp_json["data"]["requestID"])

    def _post(self, url, headers):
        retry_attempts = 1
        while retry_attempts >= 0:
            retry_attempts -= 1
            resp = requests.post(url, headers=headers)
            if resp.status_code == 401:
                logging.warning("401 Unauthorized (access token has probably expired)")
                self.tokens.refresh_tokens_from_web()
                headers["Authorization"] = "Bearer {}".format(self.tokens.get_access_token())
            else:
                break
        resp.raise_for_status()
        return resp

    def _get(self, url, headers):
        retry_attempts = 1
        while retry_attempts >= 0:
            retry_attempts -= 1
            resp = requests.get(url, headers=headers)
            if resp.status_code == 401:
                logging.warning("401 Unauthorized (access token has probably expired)")
                self.tokens.refresh_tokens_from_web()
                headers["Authorization"] = "Bearer {}".format(self.tokens.get_access_token())
            else:
                break
        resp.raise_for_status()
        return resp
