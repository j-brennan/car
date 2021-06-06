import configparser
import csv
import glob
import json
import os
import logging

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


class Reports:
    """Generate reports based on historical vehicle and charge data."""

    @staticmethod
    def generate_charge_report():
        """Generate a charge report based on historical charge report data files."""

        logging.info("Generating a charge report")
        report_filename = "reports/charge_report.csv"

        with open(report_filename, mode="w") as csv_charge_file:
            fields = {
                # <csv header name>              : <path to value within status data>
                "timestamp"                      : ["requestTimestamp"],
                "car_captured_timestamp"         : ["data", "chargingStatus", "carCapturedTimestamp"],
                "max_charge_current_ac"          : ["data", "chargingSettings", "maxChargeCurrentAC"],
                "plug_connection_state"          : ["data", "plugStatus", "plugConnectionState"],
                "charging_state"                 : ["data", "chargingStatus", "chargingState"],
                "plug_lock_state"                : ["data", "plugStatus", "plugLockState"],
                "charge_power_kw"                : ["data", "chargingStatus", "chargePower_kW"],
                "charge_rate_kmph"               : ["data", "chargingStatus", "chargeRate_kmph"],
                "target_soc_pct"                 : ["data", "chargingSettings", "targetSOC_pct"],
                "current_soc_pct"                : ["data", "batteryStatus", "currentSOC_pct"],
                "remaining_charging_time_m"      : ["data", "chargingStatus", "remainingChargingTimeToComplete_min"],
                "cruising_range_electric_km"     : ["data", "batteryStatus", "cruisingRangeElectric_km"],
                "climatisation_state"            : ["data", "climatisationStatus", "climatisationState"],
                "remaining_climatisation_time_m" : ["data", "climatisationStatus", "remainingClimatisationTime_min"]
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

            for filename in sorted(glob.glob(filename_pattern)):
                with open(os.path.join(os.getcwd(), filename), "r") as json_file:
                    logging.info("Processing status file: %s", filename)

                    data = json.load(json_file)

                    if "data" not in data or not data["data"]:
                        continue

                    details = {}

                    for fieldname, value_keys in fields.items():
                        value = data
                        for value_key in value_keys:
                            if value_key not in value:
                                raise RuntimeError("Unable to find '{}' value using path: {}".format(fieldname, value_keys))
                            value = value[value_key]
                        details[fieldname] = value

                    csv_writer.writerow(details)

        logging.info("Charge report stored at: %s", report_filename)


if __name__ == "__main__":
    Reports.generate_charge_report()
