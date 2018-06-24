# csrmesh-mqtt
A middleware enabling CSRMesh smart bulbs to be controlled over MQTT.

# Requirements
  * Python 3.x (may work on 2.x but not tested)
  * Bluez supported Bluetooth 4.0 LE (Low Energy) interface.
  * csrmesh Python library, version 0.9.0 or later.
  * MQTT broker

# Usage
     python3 ./csrmesh-mqtt-bridge.py <config path>

# Configuration
  Refer to provided example config sample. Connections are attempted to nodes in the order that thier MAC addresses are listed.

## Home Assistant configuration example
     - platform: mqtt
       name: "CSRMesh Bulb 2"
       command_topic: "csrmesh/2"
       brightness_command_topic: "csrmesh/2"
       on_command_type: "brightness"
       payload_off: 0
       payload_on: 255

# MQTT API
  Messages containing the desired brightness represented as a number from 0 to 255 are to be sent to the configured base topic, with the desired destination CSRMesh object ID appended. For example, to send to csrmesh object 2 if the configured base topic is 'csrmesh/', the MQTT message should be sent to 'csrmesh/2'. For further documentation regarding the CSRMesh object IDs, refer to the documentation for the CSRMesh Python library at: https://github.com/nkaminski/csrmesh/blob/master/README.md
