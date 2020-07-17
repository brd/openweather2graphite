#!/usr/bin/env python3

import json
import os
import requests
import sched
import socket
import time


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def publish_to_carbon(config, path, value):
  print(f'publish(): path: {path}, value: {value}')
  now = str(time.time())
  try:
    config['sock'].sendto(bytes(path + " " + str(value) + " " + now, 'utf-8'), (config['carbon_server'], config['carbon_port']))
  except Exception as e:
    print(f'Error: {str(e)}')


def poll_openweather_api(config):
  # api.openweathermap.org/data/2.5/weather?zip={zip code},{country code}&appid={your api key}
  payload = {
    "zip": config["zip_code"],
    "appid": config["openweather_key"],
    "units": "metric"
  }
  r = requests.get(OPENWEATHER_URL, params=payload)

  res = None
  try:
    res = r.json()
  except Exception as e:
    print(f'Error: {str(e)}')

  if "main" in res:
    for x in ['temp', 'feels_like', 'temp_min', 'temp_max', 'pressure', 'humidity' ]:
      if x == "humidity":
        publish_to_carbon(config, 'house/humidity/openweather_humidity', res['main']['humidity'])
      if x.startswith('temp') or x == 'feels_like':
        publish_to_carbon(config, 'house/temperature/openweather_' + x, res['main'][x])
      if x == 'pressure':
        # ignore for now
        pass


def read_config():
  if os.path.exists('config.json'):
    try:
      with open('config.json') as f:
        config = json.load(f)
    except Exception as e:
      print(f'Error opening and reading: {filename}: {str(e)}')
      sys.exit(2)

  return config


def schedule_next(config):
  config['s'].enter(600, 1, schedule_next, argument=(config,))
  poll_openweather_api(config)


def main():
  config = read_config()
  print(f'carbon_server: {config["carbon_server"]}')

  # Setup the scheduler
  config['s'] = sched.scheduler()
  config['s'].enter(2, 1, schedule_next, argument=(config,))

  # Setup the UDP socket
  try:
    config['sock'] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  except:
    print(f'Cannot create UDP socket')
    sys.exit(2)

  # Run
  config['s'].run()

if __name__ == '__main__':
  main()

