# koyu.space App Push Service

The koyu.space Push Service backend for the app.

## Requirements

- Python 3 with PIP

## Setup

Install the requirements with `sudo pip3 install -r requirements.txt` and run the `start.sh` file

## Caveats

* The push service may stop working after a few days, this has something to do with the devices refreshing their tokens in this period
* Sometimes the connection to the server may get lost

How to fix this? Just create a cronjob that restarts the backend every 2-3 days. The `start.sh` script should do this automatically, but this hasn't been proven to be a good enough solution.