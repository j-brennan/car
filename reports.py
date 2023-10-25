import configparser
import csv
import glob
import json
import os
import logging

from datetime import datetime

logging.basicConfig(
    filename="log/reports.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    force=True
)

logging.getLogger().addHandler(logging.StreamHandler())

config = configparser.ConfigParser()
config.read("config.ini")


class ChargingSession:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.charge_type = None
        self.start_soc = None
        self.end_soc = None
        self.start_range = None
        self.end_range = None

    def print_summary(self):
        if self.start_time is None and self.end_time is None:
            print("No data available for this charging session.\n")
            return

        range_added = "-"
        if self.start_range is not None and self.end_range is not None:
            range_added = self.end_range - self.start_range

        soc_added = "-"
        if self.start_soc is not None and self.end_soc is not None:
            soc_added = self.end_soc - self.start_soc

        start_time = datetime.fromisoformat(self.start_time[:-1])
        end_time = datetime.fromisoformat(self.end_time[:-1])
        duration = end_time - start_time

        weekday_name = start_time.strftime("%A")
        day_of_month = start_time.strftime("%d")
        month_name = start_time.strftime("%B")
        year = start_time.strftime("%Y")

        print(f"{weekday_name} {day_of_month} {month_name}, {year}:")
        print(f"    type        : {self.charge_type} charging session")
        print(f"    Range added : {range_added:,} km")
        print(f"    SOC added   : {soc_added}% ({self.start_soc}% => {self.end_soc}%)")
        print(f"    Duration    : {duration} ({self.start_time} => {self.end_time})\n")


class Reports:
    """Generate reports based on historical vehicle and charge data."""

    @staticmethod
    def generate_charge_report():
        """Generate a charge report based on historical charge report data files."""

        logging.info("Generating a charge report\n")
        report_filename = "reports/charge_report.csv"

        with open(report_filename, mode="w") as csv_charge_file:
            fields = {
                # <csv header name>              : <path to value within status data>
                "timestamp"                      : ["requestTimestamp"],
                "car_captured_timestamp"         : ["charging", "chargingStatus", "value", "carCapturedTimestamp"],
                "odometer"                       : ["measurements", "odometerStatus", "value", "odometer"],
                "plug_connection_state"          : ["charging", "plugStatus", "value", "plugConnectionState"],
                "charging_state"                 : ["charging", "chargingStatus", "value", "chargingState"],
                "plug_lock_state"                : ["charging", "plugStatus", "value", "plugLockState"],
                "max_charge_current_ac"          : ["charging", "chargingSettings", "value", "maxChargeCurrentAC"],
                "charge_type"                    : ["charging", "chargingStatus", "value", "chargeType"],
                "charge_power_kw"                : ["charging", "chargingStatus", "value", "chargePower_kW"],
                "charge_rate_kmph"               : ["charging", "chargingStatus", "value", "chargeRate_kmph"],
                "target_soc_pct"                 : ["charging", "chargingSettings", "value", "targetSOC_pct"],
                "current_soc_pct"                : ["charging", "batteryStatus", "value", "currentSOC_pct"],
                "remaining_charging_time_m"      : ["charging", "chargingStatus", "value", "remainingChargingTimeToComplete_min"],
                "cruising_range_electric_km"     : ["charging", "batteryStatus", "value", "cruisingRangeElectric_km"],
                "climatisation_state"            : ["climatisation", "climatisationStatus", "value", "climatisationState"],
                "remaining_climatisation_time_m" : ["climatisation", "climatisationStatus", "value", "remainingClimatisationTime_min"]
            }

            csv_writer = csv.DictWriter(
                csv_charge_file,
                fieldnames=fields.keys(),
                extrasaction="ignore",
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL
            )

            csv_writer.writeheader()

            status_filename = config.get("settings", "vehicle_status_file")
            filename_pattern = status_filename[:status_filename.find("%")] \
                + "*" \
                + status_filename[status_filename.rfind("."):]

            charging_session = ChargingSession()

            for filename in sorted(glob.glob(filename_pattern)):
                with open(os.path.join(os.getcwd(), filename), "r") as json_file:
                    # logging.info("Processing status file: %s", filename)

                    data = json.load(json_file)

                    # if "data" not in data or not data["data"]:
                    #     continue

                    pre_2022dec_format = False
                    if "data" in data:
                        pre_2022dec_format = True

                    details = {}

                    for fieldname, value_keys in fields.items():
                        value = data
                        for idx, value_key in enumerate(value_keys):
                            if idx == 0 and len(value_keys) > 1 and pre_2022dec_format:
                                value_key = "data"
                            if value_key == "value" and pre_2022dec_format:
                                continue
                            if value_key not in value:
                                # raise RuntimeError("Unable to find '{}' value using path: {}".format(fieldname, value_keys))
                                value = "-"
                            else:
                                value = value[value_key]
                        details[fieldname] = value

                    if details["charging_state"] == "charging":
                        # start of new session or continuation of existing
                        if charging_session.start_time is None:
                            charging_session.start_time = details["car_captured_timestamp"]
                            charging_session.charge_type = details["charge_type"]
                            charging_session.start_soc = details["current_soc_pct"]
                            charging_session.start_range = details["cruising_range_electric_km"]
                    else:
                        if charging_session.start_time is not None:
                            # end of existing session
                            charging_session.end_time = details["car_captured_timestamp"]
                            charging_session.end_soc = details["current_soc_pct"]
                            charging_session.end_range = details["cruising_range_electric_km"]
                            charging_session.print_summary()
                            charging_session = ChargingSession()

                    csv_writer.writerow(details)

        logging.info("Charge report stored at: %s", report_filename)


if __name__ == "__main__":
    Reports.generate_charge_report()
