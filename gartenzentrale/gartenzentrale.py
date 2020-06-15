import sys
import time
import threading
import json
import subprocess
from azure.iot.device import IoTHubDeviceClient, Message
from azure.iot.device.exceptions import *
from azure.iot.device.common.transport_exceptions import ConnectionFailedError as ConnectionFailedError2
from git import Repo
from threading import Lock
# global counters
RECEIVED_MESSAGES = 0
CONNECTION_STRING = open(".connectionstring", "r").read()
try:
    import RPi.GPIO as GPIO
except:
    print("WARNING: Emulating Relay Board")
    class GPIO:
        HIGH = None
        LOW = None
        OUT = None
        BOARD = None
        @classmethod
        def setup(cls, *args):
            pass
        @classmethod
        def output(cls, *args):
            pass
        @classmethod
        def setmode(cls, *args):
            pass
        @classmethod
        def setwarnings(cls, *args):
            pass

import time

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

class Relay:
    ''' Class to handle Relay
    Arguments:
    relay = string Relay label (i.e. "RELAY1","RELAY2","RELAY3","RELAY4")
    '''
    relaypins = {"RELAY1":15, "RELAY2":13, "RELAY3":11, "RELAY4":7}


    def __init__(self, relay):
        self.pin = self.relaypins[relay]
        self.relay = relay
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)

    def on(self):
        print(self.relay + " - ON")
        GPIO.output(self.pin,GPIO.HIGH)

    def off(self):
        print(self.relay + " - OFF")
        GPIO.output(self.pin,GPIO.LOW)

class Gartenlaube:
    def __init__(self, client):
        self.update_lock = Lock()
        if self.in_update():
            #lock up again
            self.update_lock.acquire()
        self.relais_lock1 = Lock()
        self.relais_lock2 = Lock()
        self.relais_lock3 = Lock()
        self.relais_lock4 = Lock()

        self.relais1 = Relay("RELAY1")
        self.relais2 = Relay("RELAY2")
        self.relais3 = Relay("RELAY3")
        self.relais4 = Relay("RELAY4")

        self.client = client

        twin = self.client.get_twin()
        print(twin)
        self.manual_overwrite(relay=1, value=twin["desired"].get("relay1", 0))
        self.manual_overwrite(relay=2, value=twin["desired"].get("relay2", 0))
        self.manual_overwrite(relay=3, value=twin["desired"].get("relay3", 0))
        self.manual_overwrite(relay=4, value=twin["desired"].get("relay4", 0))

        self.git = Repo(".")

    def in_update(self):
        """check if we are in the update phase"""
        return False

    def turn_everything_off(self):
        self.manual_overwrite(relay=1, value=0)
        self.manual_overwrite(relay=2, value=0)
        self.manual_overwrite(relay=3, value=0)
        self.manual_overwrite(relay=4, value=0)

    def manual_overwrite(self, relay, value, client=None):
        if relay == 1:
            relais = self.relais1
            lock = self.relais_lock1
        elif relay == 2:
            relais = self.relais2
            lock = self.relais_lock2
        elif relay == 3:
            relais = self.relais3
            lock = self.relais_lock3
        elif relay == 4:
            relais = self.relais4
            lock = self.relais_lock4
        lock.acquire()
        if value == 0:
            relais.off()
        elif value == 1:
            relais.on()
        lock.release()


    def update(self):
        self.update_lock.acquire()
        #get git commit
        current_commit = self.git.head.commit.hexsha
        with open(".before_update", "w") as f:
            f.write(current_commit)
        subprocess.run(
            "git checkout master",
            text=True,
            shell=True,
            stdout=subprocess.PIPE
        ) # in case we're in a detached head space from failed updates
        git_pull = subprocess.run(
            "git pull",
            text=True,
            shell=True,
            stdout=subprocess.PIPE
        )
        git_pull_output = git_pull.stdout
        print(git_pull_output, flush=True)
        

        if "requirements.txt" in git_pull_output:
            pip = git_pull = subprocess.run(
                "pip3 install -r requirements.txt",
                text=True,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if pip.returncode != 0:
                print("pip failed, let's hope for the best")
                print(pip.stderr)
        self.update_lock.release()
        if "Already up-to-date." in git_pull_output or "Already up to date." in git_pull_output:
            return
        sys.exit(0)

    def receive_message_listener(self):
        global RECEIVED_MESSAGES
        while True:
            try:
                message = self.client.receive_message("input1", timeout=5)   # blocking call
                if not message:
                    continue
            except ConnectionFailedError as e:
                print("connection failed")
                return
            except ConnectionFailedError2 as e:
                return
            except Exception as e:
                print(type(e))
                return
            RECEIVED_MESSAGES += 1
            print("Message received on input1")
            print( "    Data: <<{}>>".format(message.data) )
            print( "    Properties: {}".format(message.custom_properties))
            print( "    Total calls received: {}".format(RECEIVED_MESSAGES))

            try:
                payload = json.loads(message.data)
                if payload.get("command", "") == "update":
                    self.update()
            except json.JSONDecodeError as e:
                print("No valid JSON in Message")

    
    def receive_twin_listener(self):
        # This listener function only triggers for messages sent to "input1".
        # Messages sent to other inputs or to the default will be silently discarded.
        global RECEIVED_MESSAGES
        while True:
            try:
                patch = self.client.receive_twin_desired_properties_patch(timeout=5)
                if not patch:
                    continue
            except ConnectionFailedError as e:
                print("connection failed")
                return
            except ConnectionFailedError2 as e:
                # print(type(e))
                return
            except Exception as e:
                print(type(e), "hilfe")
                return
            RECEIVED_MESSAGES += 1
            print("Patch received")
            print( "    Data: \n{}".format(json.dumps(patch, indent=4)))

            for key in patch:
                if key == "relay1"  :
                    self.manual_overwrite(relay=1, value=patch[key])
                elif key == "relay2":
                    self.manual_overwrite(relay=2, value=patch[key])
                elif key == "relay3":
                    self.manual_overwrite(relay=3, value=patch[key])
                elif key == "relay4":
                    self.manual_overwrite(relay=4, value=patch[key])

def iothub_client_init():
    # Create an IoT Hub client
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    return client

def _thread1(laube):
    laube.receive_message_listener()
def _thread2(laube):
    laube.receive_twin_listener()

def main():
    
    try:
        print ( "\nPython {}\n".format(sys.version) )
        print ( "IoT Hub Client for Python" )

        client = iothub_client_init()
        # client.connect()
        laube = Gartenlaube(client)
    
        git = Repo(".")
        print("Git Status: At commit {}".format(git.head.commit))
        
        # Begin listening for messages
        message_listener_thread = threading.Thread(target=_thread1, args=(laube,))
        message_listener_thread.daemon = True
        message_listener_thread.start()

        # twin_listener_thread = threading.Thread(target=_thread2, args=(laube,))
        # twin_listener_thread.daemon = True
        # twin_listener_thread.start()

        print ( "Starting the IoT Hub Python sample...")
        print(json.dumps(client.get_twin(), indent=4))
        client.patch_twin_reported_properties({
            "software":
                {
                    "commit":git.head.commit.hexsha,
                    "log": git.head.commit.message,
                    "published": git.head.commit.authored_datetime.isoformat(),
                    "author": git.head.commit.author.name
                }
            }
        )

        print ( "The sample is now waiting for messages and will indefinitely.  Press Ctrl-C to exit. ")


        # 
        while True:
            message_listener_thread.join(timeout=1)
            if not message_listener_thread.is_alive():
                sys.exit(1)
            # twin_listener_thread.join(timeout=1)
            # if not twin_listener_thread.is_alive():
            #     sys.exit(1)
            # print(twin_listener_thread.is_alive, message_listener_thread.is_alive)

    except KeyboardInterrupt:
        print ( "IoTHubClient sample stopped" )
    except Exception as e:
        print ( "Unexpected error from IoTHub", e)
        return
    finally:
        laube.turn_everything_off()

