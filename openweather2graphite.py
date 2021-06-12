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


def poll_openweather_api(config, zip):
  # api.openweathermap.org/data/2.5/weather?zip={zip code},{country code}&appid={your api key}
  payload = {
    "zip": zip,
    "appid": config["openweather_key"],
    "units": config["units"]
  }
  try:
    r = requests.get(OPENWEATHER_URL, params=payload)
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

          if zip != 80020:
            publish_to_carbon(config, 'weather/' + str(zip) + '/openweather_' + x, res['main'][x])
          else:
            publish_to_carbon(config, 'house/' + second + '/openweather_' + x, res['main'][x])
          # The OpenWeather API only updates every 10 minutes, so fill in
          # the gaps in the graph with the same value every 60 seconds for
          # the rest of the 10 minute period
          if zip != 80020:
            config['s'].enter(60, 1, publish_to_carbon, argument=(config, 'weather/' + str(zip) + '/openweather_' + x, res['main'][x]))
            continue
          else:
            config['s'].enter(60, 1, publish_to_carbon, argument=(config, 'house/' + second + '/openweather_' + x, res['main'][x]))

      if "clouds" in res:
        if zip != 80020:
          publish_to_carbon(config, 'weather/' + str(zip) + '/openweather_clouds', res['clouds']['all'])
          config['s'].enter(60, 1, publish_to_carbon, argument=(config, 'weather/' + str(zip) + '/openweather_clouds', res['clouds']['all']))
        else:
          publish_to_carbon(config, 'house/clouds/openweather_clouds', res['clouds']['all'])
          config['s'].enter(60, 1, publish_to_carbon, argument=(config, 'house/clouds/openweather_clouds', res['clouds']['all']))
      # rain/snow
      for x in ['rain', 'snow']:
        if x in res:
          print(f'x: {x}')
          for y in ['1h', '3h']:
            if zip != 80020:
              publish_to_carbon(config, 'weather/' + str(zip) + '/openweather_' + x + '_' + y, res[x][y])
              config['s'].enter(60, 1, publish_to_carbon, argument=(config, 'weather/' + str(zip) + '/openweather_' + x + '_' + y, res[x][y]))
            else:
              publish_to_carbon(config, 'house/' + x + '/openweather_' + x + '_' + y, res[x][y])
              config['s'].enter(60, 1, publish_to_carbon, argument=(config, 'house/' + x + '/openweather_' + x + '_' + y, res[x][y]))

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
  config['s'].enter(120, 1, schedule_next, argument=(config,))
  if isinstance(config["zip_code"], list):
    for zip in config["zip_code"]:
      poll_openweather_api(config, zip)
  else:
    poll_openweather_api(config, config["zip_code"])


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

