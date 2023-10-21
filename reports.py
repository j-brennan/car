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

            for filename in sorted(glob.glob(filename_pattern)):
                with open(os.path.join(os.getcwd(), filename), "r") as json_file:
                    logging.info("Processing status file: %s", filename)

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

                    csv_writer.writerow(details)

        logging.info("Charge report stored at: %s", report_filename)


if __name__ == "__main__":
    Reports.generate_charge_report()
