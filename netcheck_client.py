import requests, time
from datetime import datetime

STATUS_UNKNOWN      = 0
STATUS_CONNECTED    = 1
STATUS_DISCONNECTED = 2



def can_connect(url):
    try:
        requests.get(url, timeout=3)
    except requests.exceptions.ConnectionError:
        return False
    return True

# Use a list of URLs instead of one to avoid the server
# thinking we perform a hacker attack
urls = [
    "http://www.google.com",
    "http://www.amazon.com",
    "http://www.ebay.com"
]

last_url_index = 0
def is_connected():
    global last_url_index
    global urls
    last_url_index += 1
    if last_url_index >= len(urls):
        last_url_index = 0
    return can_connect(urls[last_url_index])

print("Hit CTRL-C to end")
status = STATUS_UNKNOWN
timestamp = datetime.now()
try:
    while True:
        if is_connected():
            if status != STATUS_CONNECTED:
                timestamp2 = datetime.now()
                print("{0}: CONNECTED    (offline for {1} s)".format(
                    timestamp2.strftime("%Y-%m-%d %H:%M:%S"),
                    (timestamp2-timestamp).total_seconds()
                ))
                status = STATUS_CONNECTED
                timestamp = datetime.now()
        else:
            if status != STATUS_DISCONNECTED:
                timestamp2 = datetime.now()
                print("{0}: DISCONNECTED (online for {1} s)".format(
                    timestamp2.strftime("%Y-%m-%d %H:%M:%S"),
                    (timestamp2-timestamp).total_seconds()
                ))
                status = STATUS_DISCONNECTED
                timestamp = datetime.now()
        time.sleep(5)
except KeyboardInterrupt:
    print("Bye")


