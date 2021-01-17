#!/usr/bin/python3
# -*- coding: utf-8 -*
import paho.mqtt.client as paho
import atexit, time
import json, serial, sys
from datetime import datetime

broker = "localhost"
allowedCommands = {"UP", "DOWN", "MY"}
actionMap = {
    "UP": "2",
    "DOWN": "4",
    "MY": "1",
    "PROG": "8"
}
logFile = "/var/log/openhab/somfycul.log"

def handle_somfy_command(shutterName, shutterCommand):
  actionKey = actionMap[shutterCommand]
  fileName = "/var/lib/openhab/somfycul/" + shutterName + ".data"
  data = None
  rollingCode = None
  address = None
  # read properties file
  with open(fileName) as json_file:
    data = json.load(json_file)
    rollingCode = data["rollingCode"]
    address = data["address"]

  # prepare and send command
  culCommand = "YsA1" + actionKey + "0" + ("%0.4X" % rollingCode) + address
  port = serial.Serial('/dev/ttyUSB0', 38400, timeout=1)
  time.sleep(2)
  print ("sending: " + culCommand)
  port.write("Yr2\n".encode())
  port.write((culCommand + "\n").encode())
  time.sleep(3) # needed to propate over serial

  # write properties file
  with open(fileName, 'w') as json_file:
    data["rollingCode"] = (rollingCode+1) %  65535
    data["lastCommandSent"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    data["shutterName"] = shutterName
    data["command"] = shutterCommand
    json.dump(data, json_file)

  # write to logs file
  with open(logFile, 'a') as log_file:
    json.dump(data, log_file)
    log_file.write("\n")

def on_connect(client, userdata, flags, rc):
  print("Connected")

def on_disconnect(client, empty, rc):
  print("Disconnected")

def on_message(client, userdata, message):
  try:
    payload = str(message.payload.decode("utf-8"))
    print("message received: {}".format(str(payload)))
    print("message topic: {}".format(message.topic))
    shutter = message.topic[len("somfycul/command/"):]
    command = payload
    if shutter is None or command not in allowedCommands:
      print("ignoring command: {} for shutter: {}".format(command, shutter))
      return
    print("executing command: {} for shutter: {}".format(command, shutter))
    handle_somfy_command(shutter, command)
  except:
    print("Error:", sys.exc_info()[0])

def main():
  run = True

  def on_kill(client):
    client.loop_stop()
    run = False

  client = paho.Client("client-001")
  client.on_message=on_message
  client.on_connect = on_connect
  client.on_disconnect = on_disconnect
  client.reconnect_delay_set(min_delay=3, max_delay=30)

  print("connecting to broker: ", broker)
  client.connect(broker)
  client.loop_start()
  print("subscribing")
  client.subscribe("somfycul/command/#")
  print("mqtt client started")

  atexit.register(on_kill, client)
  while run:
    time.sleep(1000)


main()
