import sys
import time
import threading
import json
from azure.iot.device import IoTHubDeviceClient, Message
from git import Repo
# global counters
RECEIVED_MESSAGES = 0
CONNECTION_STRING = open(".connectionstring", "r").read()
def iothub_client_init():
    # Create an IoT Hub client
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    return client

def receive_message_listener(client):
    # This listener function only triggers for messages sent to "input1".
    # Messages sent to other inputs or to the default will be silently discarded.
    global RECEIVED_MESSAGES
    while True:
        message = client.receive_message("input1")   # blocking call
        RECEIVED_MESSAGES += 1
        print("Message received on input1")
        print( "    Data: <<{}>>".format(message.data) )
        print( "    Properties: {}".format(message.custom_properties))
        print( "    Total calls received: {}".format(RECEIVED_MESSAGES))

def main():
    try:
        print ( "\nPython {}\n".format(sys.version) )
        print ( "IoT Hub Client for Python" )

        client = iothub_client_init()
        git = Repo(".")
        print("Git Status: At commit {}".format(git.head.commit))
        # Begin listening for messages
        message_listener_thread = threading.Thread(target=receive_message_listener, args=(client,))
        message_listener_thread.daemon = True
        message_listener_thread.start()

        print ( "Starting the IoT Hub Python sample...")
        print(json.dumps(client.get_twin(), indent=4))

        print ( "The sample is now waiting for messages and will indefinitely.  Press Ctrl-C to exit. ")



        while True:
            time.sleep(1000)

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
        sys.exit(1)
