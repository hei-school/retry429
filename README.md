# retry429

An HTTP proxy that retries requests ending into 429 status code.
Can also retry any other status code depending on the provided configuration.

## Usage

1. Deploy `retry429` into your AWS:
   `sam build && sam deploy --parameter-overrides "TargetHostTemplate=jsonplaceholder.typicode.com TargetProtocol=https RetriedHttpStatuses=429,503" --guided`.
   Additional parameters can be provided, such as `SafeParamsChars`,
   read `template.yaml` for exhaustive list of available parameters.
   The url of the deployed proxy is outputed by SAM into the `Retry429HttpApiUrl` variable.
2. `Retry429HttpApiUrl` now proxies all HTTP calls to `jsonplaceholder.typicode.com`, and retries those that end into 429 and 503.

## Tests

Tests are defined in the `tests` folder in this project. Use PIP to install the test dependencies and run tests.

```bash
$ pip install -r tests/requirements.txt --user
$ python -m pytest tests/unit -v
```