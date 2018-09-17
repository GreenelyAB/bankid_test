# Yo
To test BankID you first need to set up the BankID with a test account.
Head over to [here](https://demo.bankid.com/) and click
_Log in with a Production-BankID_. Create a test account using any personal
number you desire. Once you have entered the number and a name, you'll get an
activation code. Open up the BankID app on your phone and enter it **(Note:
on Android you need to use the test version of the app. Here is
the [APK](https://www.bankid.com/assets/bankid/rp/BankID_7.11.0.31_CUSTOMERTEST.apk)).

Also, here is the official [documentation](https://www.bankid.com/assets/bankid/rp/bankid-relying-party-guidelines-v3.2.1.pdf)

## The general flow
When the user reaches a point in the front end app where a sign is required,
Greenely has to tell BankID to start a signing process on the users phone. This
is done trough an API call to BankID. This call has to be encrypted using keys
issued by a bank collaborating with BankID, so we need to do this call
serverside in order to not expose those keys to the user.

When the call to BankID has been made, BankID calls the users BankID app to
start the signing process and returns among other things `autoStartToken`.

The `autoStartToken` can be used by the front end app to start the BankID
app for the user automatically. See chapter 3 in the official documentation for
more info on this. Note that if the app is not started automatically for the
user, the user can still manually switch to the BankID app where the process
should be initiated.

When the user is signing the request, the backend has to periodically ask the
BankID API whether the user has completed the signing. The answer from BankID
will contain a status, and if the signing has been completed by the user the
status response will contain the signature.

To see more details about the signing process, see chapter 14.1 in the official
documentation.

### Creating a sign request
```
sign = client.sign(
    end_user_ip=ip_address,
    user_visible_data=b64encode('Allow Greenely'),
    personal_number=personal_number)
```

### Polling
```
client.collect(order_ref=order_ref)
```

When polling, the format for the response is
```
{
  status: 'pending',
  hintCode: 'outstandingTransaction',
  orderRef: '2da9585f-82bd-46bf-bcbc-75a0653ea6c8'
}
```
To see more examples of how the responses might look, including a "success"
response, see section 14.2 in the official documentation.

There are a number of different hintCodes that will help you show the correct
messages to the user, see section 6. Recommended messages for details.


## The test app
I've written a very basic app that signs trough BankID. I've implemented some test
exceptions but more importantly i've tried to highlight some findings I've made
that I think might be helpful.

Run the app (install the requirements first):
```
gunicorn main:app --bind 0.0.0.0:8000
```

Enjoy and good luck!
