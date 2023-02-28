import logging
import requests
import sys
from car import Car

logging.basicConfig(
    filename="log/car.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    force=True
)

logging.getLogger().addHandler(logging.StreamHandler())


def main(command):
    car = Car()

    if command == "status":
        car.get_status()
    elif command == "start-charging":
        car.set_charging("start")
    elif command == "stop-charging":
        car.set_charging("stop")
    elif command == "vehicles":
        car.get_vehicles()
    else:
        print("Unsupported command: " + command)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        command = sys.argv[1]
    else:
        print("No command specified")
        exit(-1)

    try:
        main(command)
    except requests.exceptions.HTTPError as e:
        logging.error("Error: " + str(e))
    except Exception as e:
        logging.exception("Exception processing: " + command)
        logging.exception("Exception: " + str(e))
