# car

## Configuration

Create a new `config.ini` file using the sample `config.ini.template`:

    cd car
    cp config.ini.template config.ini

Edit `config.ini` and enter your user details to log into your account:

    email = my@email.com
    password = mypassword

## Usage

### Get the car's status:

    python main.py status

The complete status data is stored in a json file in the `output` directory.

### Start charging:

    python main.py start-charging

A status check is performed first to see if the charging cable is plugged in and that the car is not already charging.

### Stop charging:

    python main.py stop-charging

A status check is performed first to see if the charging cable is plugged in and that the car is currently charging.

### Produce csv data from status files:

    python reports.py

Reads all the json files in the `output` directory and produces a single csv file using data from the most interesting fields.

## macOS installation

    brew install pyenv
    pyenv install 3.9.4
    pyenv global 3.9.4
    pip3 install requests
    pip3 install beautifulsoup4

## Ubuntu installation

    sudo apt install python3-pip
    sudo pip3 install beautifulsoup4

## crontab settings

Create a cronjob to start or stop charging (see https://crontab.guru/):

    crontab -e

Sample crontab settings:

**NOTE:** Change path to reflect your own location to the car project files!

    HOME=/path/to/car

    # start charging at 00:05 (and 00:07 just in case!)
    5 0 * * * /usr/bin/python3 /path/to/car/main.py start-charging
    7 0 * * * /usr/bin/python3 /path/to/car/main.py start-charging

    # get status every 15 minutes between 00:00 and 09:00
    #*/15 0-9 * * * /usr/bin/python3 /path/to/car/main.py status
