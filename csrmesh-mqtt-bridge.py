#!/usr/bin/python3

from multiprocessing import Process, Queue, Value
from yaml import load
import queue
import time

def mqtt_proc(q, mqtt_basetopic, mqtt_host, mqtt_port, mqtt_user, mqtt_pass):
    import paho.mqtt.client as mqtt

    def on_connect(mqttc, obj, flags, rc):
        if rc == 0:
            print("[+] MQTT connection successful")
        else:
            print("[-] MQTT connection failed: "+mqtt.connack_string(rc))
            time.sleep(5.0)

    def on_subscribe(mqttc, obj, mid, granted_qos):
        print("[+] Subscribed to MQTT with QoS: " + str(granted_qos[0]))

    def on_message(mqttc, obj, msg):
        try:
            #Both values must be representable as integers
            objid = int(msg.topic.rpartition('/')[2])
            value = int(msg.payload)

            #Payload must be representable as an integer between 0 and 255
            if value < 0 or value > 255:
                raise ValueError

        except ValueError:
            print("[-] Invalid MQTT message received: topic \"%s\", payload \"%s\"" % (msg.topic, str(msg.payload)))
            return

        print("Set object %s to value %s" % (objid, value))

        try:
            q.put_nowait((objid,value))
        except queue.Full:
            print("[-] Message queue full, discarding message!")

    mqttc = mqtt.Client()
    if mqtt_user and mqtt_pass:
        mqttc.username_pw_set(mqtt_user, mqtt_pass)
    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_subscribe = on_subscribe
    mqttc.connect(mqtt_host, mqtt_port, 60)
    mqttc.subscribe("%s#" % (mqtt_basetopic,), 0)
    mqttc.loop_forever()

def csrmesh_proc(q, wdt_val, pin, mac_list):
    import csrmesh as cm
    from bluepy import btle
    backoff = False

    while(True):
        #Skip on 1st iteration, otherwase wait 5 sec for retrying
        if backoff:
            time.sleep(5.0)
        backoff = True

        #Try to make a connection.
        #Also keep the watchdog timer from counting up
        with wdt_val.get_lock():
            csrconn = cm.gatt.connect(mac_list,True)

        #We failed to connect, retry
        if not csrconn:
            continue
        print("[+] Connected to mesh")
        
        #For as long as we are connected, reset the WDT, and try to get and deliver a message
        while(True):
            with wdt_val.get_lock():
                wdt_val.value = 0
            try:
                oid, value = q.get(block=True, timeout=5)
            except queue.Empty:
                #Send no-op command to make connection is still alive
                cm.gatt.send_packet(csrconn,0,b'00')
                continue
            res = cm.lightbulb.set_light(csrconn,pin,value,value,value,value,oid,True)
            if not res:
                #Failed, so reconnect
                cm.gatt.disconnect(csrconn)
                break

if __name__== '__main__':
    conf = None
    #Load config file
    with open("config.yml",'r') as f:
        conf = load(f)
    #Forever
    while(1):
        #Startup
        q = Queue()
        wdt_val = Value('i',0)
        mqtt_phandle = Process(target=mqtt_proc, args=(q,conf['mqtt']['basetopic'],
                                                         conf['mqtt']['host'],
                                                         conf['mqtt']['port'],
                                                         conf['mqtt']['user'],
                                                         conf['mqtt']['pass']))
        mqtt_phandle.daemon = True
        csr_phandle = Process(target=csrmesh_proc, args=(q,wdt_val, conf['csrmesh']['pin'], conf['csrmesh']['mac_list']))
        csr_phandle.daemon = True

        #Start MQTT and csrmesh processes
        print("[+] Initializing MQTT to CSRMesh gateway")
        mqtt_phandle.start()
        csr_phandle.start()

        #Bluepy hangs when the device disappears, so restart if the WDT stops being reset
        while(wdt_val.value < 3):
            with wdt_val.get_lock():
                wdt_val.value += 1
            time.sleep(10.0)

        #Terminate processes, and reinitialize the whole system
        print("[!] bluepy unresponsive, reloading...")
        csr_phandle.terminate()
        mqtt_phandle.terminate()
