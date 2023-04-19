import requests
import json
import avereno
import logging
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def to_retryable_url(original_host, path):
    """Rewrites original url to a different one so that retry429 is not infinitely looping over itself""""
    private_host = "retryable-" + original_host
    return "http://" + private_host + path

def reject_429(response, endpoint):
    if response.status_code == 429:
        raise Exception(f"Definite 429: {endpoint}")
    if response.status_code == 500:
        raise Exception(f"Suspicious 429: {endpoint}")
    return response

def lambda_handler(event, context):
    method = event["httpMethod"]
    path = event["path"]
    endpoint = f"{method} {path}"
    headers = event["headers"]
    response = avereno.retry(
        lambda: reject_429(
            requests.request(
                method=method,
                headers=headers,
                url=to_retryable_url(headers["Host"], path),
                data=event["body"]
            ),
            endpoint
        ),
        max_sleep=datetime.timedelta(seconds=10),
        on_retry=lambda current_nb_retries, current_error: logger.error(
            f"Retry no.{current_nb_retries} after error: {current_error}"
        ),
    )
    
    return {
        "statusCode": response.status_code,
        "body": json.dumps(response.json())
    }
