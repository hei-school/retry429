# retry429

Retries HTTP requests that end into 429.
Also retries those that end into 500 as 429 are often wrongly typed into 500.

## Usage

1. Deploy into your AWS: `sam build && sam deploy --guided`
2. Define how you want to rewrite your `original_url` into `retryable_url`.
   That is, modify the `to_retryable_url` function.
   You also probably need to add the corresponding record into your DNS server.
3. Make `original_url`point to retry429.
4. Define how you want the retries to be done.
   That is, modify the parameters of `avereno.retry`.
   By default, retries are done 3 times within a timeframe of 10 seconds.
5. Perform any additional configuration for the lambda.
   Typically you want to put it into your private subnets if `retryable_url` can only be accessed there.
   You also want to configure CORS for the generated HttpAPI in API Gateway if the original calls come from browsers.
6. Monitor retried 429 through the Log Insights associated with the lambda function.
   Tell your backend developers to reduce them over time!

## Tests

Tests are defined in the `tests` folder in this project. Use PIP to install the test dependencies and run tests.

```bash
$ pip install -r tests/requirements.txt --user
$ python -m pytest tests/unit -v
```