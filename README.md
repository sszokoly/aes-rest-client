# aes-rest-client

Minimal Python client for the Avaya AES Web Telephony Interface (WTI) REST
`MakeCall` and `MakePredictiveCall` services. Raw extension numbers are
resolved through the named AES switch connection before the call is made.

Install the only runtime dependency:

```bash
python -m pip install requests
```

## `make_call()`

```python
from aes_rest_client import make_call

response = make_call(
    "1001",
    "1101",
    aes_server="https://aes.example.com",
    username="aes-user",
    password="aes-password",
    switch_name="avayacm",
)
print(response)
```

## `make_predictive_call()`

```python
from aes_rest_client import make_predictive_call

response = make_predictive_call(
    "1020",
    "1101",
    aes_server="https://aes.example.com",
    username="aes-user",
    password="aes-password",
    switch_name="avayacm",
)
print(response)
```

AES requires a TSAPI Advanced AEC license for `make_predictive_call()`. WebLM
must provide at least one of these features:

```text
VALUE_AES_AEC_SMALL_ADVANCED
VALUE_AES_AEC_MEDIUM_ADVANCED
VALUE_AES_AEC_LARGE_ADVANCED
```

Without an Advanced tier, AES rejects predictive calls with
`genericSubscribedResourceAvailability` error.


## Disclaimer

`aes_rest_client.py` is an independent tool and is not affiliated with, developed by,
endorsed by, or supported by any vendor. It is provided "as is," without
warranties of any kind, express or implied. Users are responsible for evaluating
its suitability and assume all risks associated with its use.