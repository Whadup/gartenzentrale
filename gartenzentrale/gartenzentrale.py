import sys
import time
import threading
import json
import subprocess
from azure.iot.device import IoTHubDeviceClient, Message
from git import Repo
from threading import Lock
# global counters
RECEIVED_MESSAGES = 0
CONNECTION_STRING = open(".connectionstring", "r").read()

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

        self.client = client
        self.git = Repo(".")

    def in_update(self):
        """check if we are in the update phase"""
        return False

    def update(self):
        self.update_lock.acquire()
        #get git commit
        current_commit = self.git.head.commit.hexsha
        with open(".before_update", "w") as f:
            f.write(current_commit)
        git_pull = subprocess.run(
            "git pull",
            text=True,
            shell=True,
            stdout=subprocess.PIPE
        )
        git_pull_output = git_pull.stdout
        print(git_pull_output)
        if "requirements.txt" in git_pull_output:
            pass
        self.update_lock.release()
        sys.exit(0)

def iothub_client_init():
    # Create an IoT Hub client
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    return client



def receive_message_listener(client):
    # This listener function only triggers for messages sent to "input1".
    # Messages sent to other inputs or to the default will be silently discarded.
    global RECEIVED_MESSAGES
    while True:
        try:
            message = client.receive_message("input1")   # blocking call
            RECEIVED_MESSAGES += 1
            print("Message received on input1")
            print( "    Data: <<{}>>".format(message.data) )
            print( "    Properties: {}".format(message.custom_properties))
            print( "    Total calls received: {}".format(RECEIVED_MESSAGES))

            try:
                payload = json.loads(message.data)
                if payload.get("command", "") == "update":
                    update(client=client)
            except json.JSONDecodeError as e:
                print("No valid JSON in Message")


        except:
            return

def manual_overwrite(relay, value, client=None):
    pass

def receive_twin_listener(client):
    # This listener function only triggers for messages sent to "input1".
    # Messages sent to other inputs or to the default will be silently discarded.
    global RECEIVED_MESSAGES
    while True:
        try:
            patch = client.receive_twin_desired_properties_patch()
            RECEIVED_MESSAGES += 1
            print("Patch received")
            print( "    Data: \n{}".format(json.dumps(patch, indent=4)))

            for key in patch:
                if key == "relay1":
                    manual_overwrite(relay=1, value=patch[key])
                elif key == "relay2":
                    manual_overwrite(relay=2, value=patch[key])
                elif key == "relay3":
                    manual_overwrite(relay=3, value=patch[key])
                elif key == "relay4":
                    manual_overwrite(relay=4, value=patch[key])

        except:
            return

def main():
    
    try:
        print ( "\nPython {}\n".format(sys.version) )
        print ( "IoT Hub Client for Python" )

        client = iothub_client_init()
        a = Gartenlaube(client)
        a.update()
    
        git = Repo(".")
        print("Git Status: At commit {}".format(git.head.commit))
        
        # Begin listening for messages
        message_listener_thread = threading.Thread(target=receive_message_listener, args=(client,))
        message_listener_thread.daemon = True
        message_listener_thread.start()

        twin_listener_thread = threading.Thread(target=receive_twin_listener, args=(client,))
        twin_listener_thread.daemon = True
        twin_listener_thread.start()



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


        message_listener_thread.join()
        # while True:
        #     time.sleep(1000)

    except KeyboardInterrupt:
        print ( "IoTHubClient sample stopped" )
    except Exception as e:
        print ( "Unexpected error from IoTHub", e)
        return

if __name__ == '__main__':
    try:
        main()

    except Exception as error:
        print ( error )
        # Do we need to revert to a previous version?
        sys.exit(1)
