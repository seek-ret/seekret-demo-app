from flask import Flask
from flask import request
from flask import jsonify
from time import sleep

app = Flask(__name__)


# using path parameters here for readability, but actually expecting our system to
# treat each path parameter as a new endpoint
@app.route("/microservice1/<some_route>", methods=['GET', 'POST'])
def service1(some_route):
    status_code = request.args.get("status")
    latency = request.args.get("latency")
    should_alter_response = True if request.args.get("alter_response") == "True" else False
    print(f"{should_alter_response}")

    body = request.get_json() if should_alter_response else {}

    user_message = ""
    if latency and int(latency):
        body["latency"] = f"Waiting {latency} seconds before returning result\n"
        sleep(int(latency))

    if status_code and int(status_code):
        body["status"] = f"Returning special status code {status_code}\n"
    else:
        status_code = 200
        body["status"] = f"Didn't receive any response, returning {status_code}\n"

    return jsonify(body), status_code


@app.route("/microservice2/<some_route>", methods=['GET', 'POST'])
def service2(some_route):
    return service1(some_route)
