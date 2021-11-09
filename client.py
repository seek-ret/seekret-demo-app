import requests
import argparse
from multiprocessing import Pool

# list of all paths that wil be created in change diff
stats_path = "/microservice2/stats"
responses_path = "/microservice2/responses"
responses_change_path = "/microservice2/response_change"
latency_path = "/microservice2/latency"
hidden_path = "/microservice2/hidden"
unchanged_path = "/microservice1/unchanged_path"
new_endpoint_path = "/microservice1/new_path"
type_path = "/microservice1/type_path"
not_required_path = "/microservice1/not_required"
new_param_path = "/microservice1/new_param"
deleted_endpoint_path = "/microservice1/deleted_endpoint"


class TrafficGenerator:
    request_params = {"type": 4,
                      "not_required": 3}
    request_headers = {"session": "4"}
    default_path = "/microservice1/default_path"

    def __init__(self, server_address, should_change):
        self.server_address = server_address
        self.should_change = should_change

    def send_request(self, req_path, req_params=None, method="GET", req_headers=None,
                     body=None, should_duplicate=True, status_assert=200):

        req_headers = req_headers if req_headers else self.request_headers
        req_params = req_params if req_path else self.request_params

        # Sending the actual request
        res = requests.request(method=method, url=self.server_address + req_path,
                               params=req_params, json=body, headers=req_headers)
        if res.status_code != status_assert:
            raise RuntimeError(f"Wrong status code received {res.status_code}, expected: {status_assert}")

        # Sending changes to the generic endpoint default_path (when needed)
        if should_duplicate:
            # This should only be POST
            res = requests.request(method='POST', url=self.server_address + self.default_path,
                                   params=req_params, json=body, headers=req_headers)
            if res.status_code != status_assert:
                raise RuntimeError(f"Wrong status code received {res.status_code}, expected: {status_assert}")

    def send_new_endpoint(self):
        if self.should_change:
            self.send_request(new_endpoint_path, should_duplicate=False)

    def send_deleted_endpoint(self):
        if not self.should_change:
            self.send_request(deleted_endpoint_path, should_duplicate=False)            

    def send_type_change(self):
        body = {"type": "session"} if self.should_change else {"type": 5}  # Should change type to string
        self.send_request(type_path, method="POST", body=body)

    def send_required_change(self):
        mod_params = self.request_params.copy()
        if self.should_change:
            del mod_params["not_required"]  # Deleting a parameter that is always shown in other requests
        self.send_request(not_required_path, mod_params)

    def send_new_param(self):
        mod_params = self.request_params.copy()
        if self.should_change:
            mod_params["new_param"] = 1
        self.send_request(new_param_path, mod_params)

    def send_response_change(self):
        # should see 'status 200' deleted, and 'status 202' added
        mod_params = self.request_params.copy()
        mod_params["status"] = 202 if self.should_change else 200
        self.send_request(responses_path, mod_params,
                          status_assert=mod_params.get("status", 200))

    def send_response_schema_change(self):
        mod_params = self.request_params.copy()
        body = {"some_added_value": "session"}
        if self.should_change:
            mod_params["alter_response"] = True
        else:
            mod_params["alter_response"] = False

        self.send_request(responses_change_path, body=body, req_params=mod_params)

    def send_latency_change(self):
        mod_params = self.request_params.copy()
        if self.should_change:
            mod_params["latency"] = 1    # latency of 1 second
        with Pool(4) as p:  # we need pool here since we don't want to wait for all requests to finish one by one
            results = []
            for _ in range(0, 3):
                result = p.apply_async(self.send_request, (latency_path,),
                                       kwds={"req_params": mod_params})
                results.append(result)
            [result.wait() for result in results]

    def send_hidden_change(self):
        mod_headers = self.request_headers.copy()
        if self.should_change:
            mod_headers["session"] = "string"
            mod_headers["new_hidden_header"] = "other_header"
        self.send_request(hidden_path, req_headers=mod_headers)  # Will also create a hidden change in default_path

    def send_stats(self):
        status_codes = [200, 202, 401, 500]  # List of status codes that will be returned in response
        mod_params = self.request_params.copy()
        counter = {"total": 0}
        for one_status in status_codes:
            counter[one_status] = 0
            for _ in range(1, 10):  # Running 10 requests for each status code
                mod_params["status"] = one_status
                self.send_request(stats_path, req_params=mod_params,
                                  status_assert=one_status, should_duplicate=False)
                counter["total"] += 1
                counter[one_status] += 1
        return counter


def main(server_address, should_change, should_calc_stats):
    generator = TrafficGenerator(server_address, should_change)

    generator.send_hidden_change()
    generator.send_latency_change()
    generator.send_new_endpoint()
    generator.send_deleted_endpoint()
    generator.send_type_change()
    generator.send_required_change()
    generator.send_new_param()
    generator.send_deleted_endpoint()
    generator.send_response_change()
    generator.send_response_schema_change()

    if should_calc_stats:
        counter = generator.send_stats()
        print(counter)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Traffic generator. make sure you activate a server before')
    parser.add_argument('server_address', metavar='server_address', type=str,
                        help='the address of the server. for example: http://testserver.com:4000')
    parser.add_argument('--second', dest='should_change', action='store_const',
                        const=True, default=False,
                        help='Should initiate a change in traffic')
    parser.add_argument('--stats', dest='should_calc_stats', action='store_const',
                        const=True, default=False,
                        help='Should initiate a stats check (check out the scripts output)')
    args = parser.parse_args()

    main(args.server_address, args.should_change, args.should_calc_stats)
