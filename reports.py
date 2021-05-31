import csv
import glob
import json
import os


class Reports:

    def charging_report():
        with open('reports/charge_report.csv', mode='w') as csv_charge_file:
            fieldnames = [
                'timestamp',
                'car_captured_timestamp',
                'max_charge_current_ac',
                'plug_connection_state',
                'charging_state',
                'plug_lock_state',
                'charge_power_kw',
                'charge_rate_kmph',
                'target_soc_pct',
                'current_soc_pct',
                'remaining_charging_time_m',
                'cruising_range_electric_km',
                'climatisation_state',
                'remaining_climatisation_time_m'
            ]

            csv_writer = csv.DictWriter(csv_charge_file, fieldnames=fieldnames, extrasaction='ignore', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writeheader()

            for filename in sorted(glob.glob('output/vehicle_status_*.json')):
                with open(os.path.join(os.getcwd(), filename), 'r') as json_file:
                    data = json.load(json_file)

                    if not data["data"]:
                        continue

                    details = {
                        'timestamp': data["requestTimestamp"],
                        'max_charge_current_ac': data["data"]["chargingSettings"]["maxChargeCurrentAC"],
                        'target_soc_pct': data["data"]["chargingSettings"]["targetSOC_pct"],

                        'car_captured_timestamp': data["data"]["chargingStatus"]["carCapturedTimestamp"],
                        'charge_power_kw': data["data"]["chargingStatus"]["chargePower_kW"],
                        'charge_rate_kmph': data["data"]["chargingStatus"]["chargeRate_kmph"],
                        'charging_state': data["data"]["chargingStatus"]["chargingState"],
                        'remaining_charging_time_m': data["data"]["chargingStatus"]["remainingChargingTimeToComplete_min"],

                        'plug_connection_state': data["data"]["plugStatus"]["plugConnectionState"],
                        'plug_lock_state': data["data"]["plugStatus"]["plugLockState"],

                        'cruising_range_electric_km': data["data"]["batteryStatus"]["cruisingRangeElectric_km"],
                        'current_soc_pct': data["data"]["batteryStatus"]["currentSOC_pct"],

                        'climatisation_state': data["data"]["climatisationStatus"]["climatisationState"],
                        'remaining_climatisation_time_m': data["data"]["climatisationStatus"]["remainingClimatisationTime_min"]
                    }

                    csv_writer.writerow(details)


if __name__ == "__main__":
    Reports.charging_report()
