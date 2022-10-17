import json
import time
import uuid
import websocket
import ssl


class Nas:
    def __init__(self, url):
        self.debug = False
        self.log = None

        # websocket.enableTrace(True)
        self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
        self.ws.connect(url)

    def debug(self, enable):
        self.debug = enable

        # if enable and self.log == None:
        #     self.log = open("log.txt", "w")
        # elif not enable and self.log != None:
        #     self.log.close()

    def log(self, log_text):
        if (self.debug):
            self.log.writelines(log_text)

    def read_file(filename):
        try:
            with open(filename) as file:
                result = json.load(file)
        except:
            print("Unable to read input file")
            exit(1)
        return result

    def write_file(filename, json_obj):
        try:
            with open(filename, "w") as file:
                json.dump(json_obj, file, indent=4)
        except:
            print("Unable to write to input file")
            exit(1)

    def send(self, request_json):
        request_str = json.dumps(request_json)
        self.ws.send(request_str)

    def recv(self):
        result_str = self.ws.recv()
        result_json = json.loads(result_str)
        return result_json

    def method(self, method, params, **kwargs):
        result = {}

        recv = True
        if 'recv' in kwargs:
            recv = kwargs['recv']

        try:
            # if self.debug:
            #     print("Method: " + method)
            #     print("Params: " + json.dumps(params, indent=4))

            request = {
                "id": str(uuid.uuid4()),
                "msg": "method",
                "method": method,
                "params": params
            }

            self.send(request)

            if recv:
                result = self.recv()

        except Exception as ex:
            print("---------- ERROR ----------")
            print("Stack trace: " + str(ex))

            print("Method: " + method)
            print("Params: " + json.dumps(params, indent=4))
            exit(1)

        return result

    def get_job(self, job_number):
        state = 'RUNNING'
        response = self.method('core.get_jobs', [[["id", "=", job_number]]])

        state = response['result'][0]['state']
        while state == "RUNNING":
            time.sleep(1)
            # print("sleep(1)")
            response = self.method(
                'core.get_jobs', [[["id", "=", job_number]]])
            state = response['result'][0]['state']

        return response['result'][0]

    def connect(self, username, password):
        result = False
        request = {
            "msg": "connect",
            "version": "1",
            "support": ["1"]
        }

        self.send(request)
        response = self.recv()

        if response['msg'] == 'connected':
            response = self.method("auth.login", [username, password])
            result = response['result']

        return result

    def disconnect(self):
        self.ws.close()
        # self.log.close()
        # self.debug(False)

    def import_pools(self):
        response = self.method("pool.import_find", [])
        job = response["result"]
        response = self.get_job(job)

        pools = response['result']

        for pool in pools:
            params = {
                "guid": pool['guid']
            }
            response = self.method("pool.import_pool", [params])

    def create_pools(self, pools):
        response = self.method("disk.query", [])

        disks = {}
        for disk in response['result']:
            disks[disk['serial']] = disk['name']

        for pool in pools:
            for topology_item in pool['topology']:
                for part in pool['topology'][topology_item]:
                    for i in range(len(part['disks'])):
                        part['disks'][i] = disks[part['disks'][i]]

            response = self.method("pool.create", [pool])
            job = response["result"]
            response = self.get_job(job)
            pass

    def create_datasets(self, datasets):
        for dataset in datasets:
            reponse = self.method("pool.dataset.create", [dataset])

    def create_users(self, users):
        for user in users:
            response = self.method("user.create", [user])

    def create_shares(self, shares):
        pass

    def create_data_protection(self, data_protections):
        response = self.method("pool.query", [])

        pools = response['result']
        for pool in pools:
            data_protections['scrub']['pool'] = pool['id']
            response = self.method("pool.scrub.create", [
                                   data_protections['scrub']])

        for pool in pools:
            if '/' not in pool['name']:
                data_protections['snapshot']['dataset'] = pool['name']
                response = self.method("pool.snapshottask.create", [
                                       data_protections['snapshot']])

        response = self.method("smart.test.create", [
                               data_protections['smart']])

    def set_network(self, networks, username, password):
        response = self.method("network.configuration.update", [
                               networks['config']])
        response = self.method("interface.update", [
                               networks['interface_id'], networks['interface']])
        response = self.method("interface.commit", [], recv=False)
        self.disconnect()
        time.sleep(5)
        self.ws.connect(
            "wss://" + networks['interface']['aliases'][0]['address'] + "/websocket")
        self.connect(username, password)
        response = self.method("interface.checkin", [])

    def set_root_email(self, email):
        params = {
            "email": email
        }
        response = self.method("user.update", [1, params])

    def set_certs(self, acme):
        response = self.method("acme.dns.authenticator.create", [
                               acme['authenticator']])
        auth_id = response['result']['id']

        response = self.method("certificate.create", [acme['csr']])
        job = response['result']
        response = self.get_job(job)
        csr_id = response['result']['id']

        acme['cert']['csr_id'] = csr_id
        for mapping in acme['cert']['dns_mapping']:
            acme['cert']['dns_mapping'][mapping] = auth_id
        response = self.method("certificate.create", [acme['cert']])
        job = response['result']
        response = self.get_job(job)
        cert_id = response['result']['id']

        acme['gui']['ui_certificate'] = cert_id
        response = self.method("system.general.update", [acme['gui']])
        response = self.method("system.general.ui_restart", [])
        pass

    def clean_dashboard(self):
        pass

    def set_container_pool(self, containers):
        params = {
            "pool": containers['pool']
        }

        response = self.method("kubernetes.update", [params])

    def containers(self, containers):
        for container in containers:
            response = self.method("chart.release.create", [container])
            pass
