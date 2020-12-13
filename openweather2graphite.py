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
    "units": config["units"]
  }
  r = requests.get(OPENWEATHER_URL, params=payload)
  try:
    if r.status_code == requests.codes.ok:
      res = None
      res = r.json()

    if "main" in res:
      for x in ['temp', 'feels_like', 'temp_min', 'temp_max', 'pressure', 'humidity' ]:
        second = "temperature"
        if x == "humidity":
          second = "humidity"
        if x == 'pressure':
          second = "pressure"

        publish_to_carbon(config, 'house/' + second + '/openweather_' + x, res['main'][x])
        # The OpenWeather API only updates every 10 minutes, so fill in
        # the gaps in the graph with the same value every 60 seconds for
        # the rest of the 10 minute period
        for t in range(60, 600, 60):
          config['s'].enter(t, 1, publish_to_carbon, argument=(config, 'house/' + second + '/openweather_' + x, res['main'][x]))
    if "clouds" in res:
      publish_to_carbon(config, 'house/clouds/openweather_clouds', res['clouds']['all'])
      for t in range(60, 600, 60):
        config['s'].enter(t, 1, publish_to_carbon, argument=(config, 'house/clouds/openweather_clouds', res['clouds']['all']))

  except Exception as e:
    print(f'Error: {str(e)}')


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

