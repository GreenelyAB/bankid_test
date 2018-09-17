from bankid import BankIDJSONClient
from bankid.exceptions import InvalidParametersError

from multiprocessing import Process
from threading import Thread
from time import sleep
from Queue import Queue
from base64 import b64encode

import falcon
import json
import jinja2

# Queue for signing processes
q = Queue()

# Like a fake database
signed_personal_numbers = {}

# RFA Messages, see section 6 in the official documentation
rfa_messages = {
    1: 'Start your BankID',
    2: 'The BankID app is not installed. Please contact your internet bank.'
    # Etc
}

# The BankID API client
client = BankIDJSONClient(
    certificates=('keys/certificate.pem', 'keys/key.pem'),
    test_server=True)

""" API RESOURCES """

class HTMLResource(object):
    def on_get(self, req, resp):
        """ Servie the HTML. Needed because we are doing CORS, so we need a
            server to make requests from """

        resp.content_type = 'text/html'
        with open('index.html', 'r') as f:
            resp.body = jinja2.Template(f.read()).render({
                'signed_personal_numbers': signed_personal_numbers
            })


class BankIDResource(object):
    def on_get(self, req, resp, personal_number):
        """ This would be the endpoint that the app calls to initiate the
            signing. You need the IP and the personal number to do the signing,
            so this endpoint accepts the personal number as a param """

        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.content_type = 'application/json'

        ip_address = req.access_route[0]

        """ Reference the documentation or
            https://github.com/hbldh/pybankid/blob/master/bankid/exceptions.py
            to see all the exceptions that you have to prepare for """

        try:
            # You can choose between signing and authenticating. We want signing
            sign = client.sign(
                end_user_ip=ip_address,
                user_visible_data=b64encode('Allow Greenely'),
                personal_number=personal_number) # Century is required
            q.put({
                'order_ref': sign['orderRef'],
                'personal_number': personal_number
            })
            resp.body = json.dumps(sign)

        except InvalidParametersError:
            resp.body = json.dumps({
                'error': 'The submitted parameters are invalid'
            })

        except Exception, e:
            """ Most of the exceptions have an rfa number attached to them.
                The RFA number is a reference to a recommended message for
                the speific error. You can thus bind the number to a message
                """
            try:
                resp.body = json.dumps({
                    'error': rfa_messages[e.rfa]
                })
            except AttributeError:
                """
                RFA Not present. This should not happen since you should
                catch all the exceptions without RFA messages before. See
                https://github.com/hbldh/pybankid/blob/master/bankid/exceptions.py
                to see what exceptions do not have rfa references
                """
                resp.body = json.dumps({
                    'error': 'Something went very wrong'
                })


""" WORKER SIMULATION """

def collect_signing(queue_item):
    """ Collect a signing. Will collect the status of the signing until complete
        or failed is returned. I guess you want to store the status in a DB here
        in production.
        The official documentation recommends you to use `hintCode` here to
        feed the user with info about the process. See 14.2.3 in the official
        documentation. """

    while True:
        """ To see which errors you should catch here, see the variable
            `_JSON_ERROR_CODE_TO_CLASS` in
            https://github.com/hbldh/pybankid/blob/master/bankid/exceptions.py
            (line 319). Basically, not all errors are thrown as an exception,
            so you need to both catch errors and also look at the response
            `hintCode`. The `Hintcode` binds to a recommended error message
            """

        try:
            response = client.collect(order_ref=queue_item['order_ref'])
            signed_personal_numbers[queue_item['personal_number']] = response

            if response['status'] == 'complete' or response['status'] == 'failed':
                break

        except NotFoundError:
            resp.body = json.dumps({
                'error': 'Crazy stuff'
            })
        # Etc...
        except Exception, e:
            # Same idea as above
            try:
                resp.body = json.dumps({
                    'error': rfa_messages[e.rfa]
                })
            except AttributeError:
                resp.body = json.dumps({
                    'error': 'Something went very wrong'
                })

        # Official documentation recommends waiting 2 seconds between each call
        sleep(2)

def worker():
    """ This simulates some kind of global worker that takes jobs from a queue """
    while True:
        item = q.get()
        # When a job is collected, a seperate process is started for that job
        Process(target=collect_signing, args=(item,)).start()
        q.task_done()

main_process = Thread(target=worker)
main_process.start()

""" The API """

app = falcon.API()

app.add_route('/bankid/{personal_number}', BankIDResource())
app.add_route('/', HTMLResource())

