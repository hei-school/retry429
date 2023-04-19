import requests
import json
import avereno
import logging
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def to_retryable_host(original_host):
    """Info(rewrite)"""
    return "private-" + original_host

def to_retryable_url(original_host, path):
    """Info(rewrite):
       Rewrites original url to a different one
       so that retry429 is not infinitely looping over itself"""
    return "http://" + to_retryable_host(original_host) + path

def reject_429(response, endpoint):
    if response.status_code == 429:
        raise Exception(f"Definite 429: {endpoint}")
    if response.status_code == 500:
        raise Exception(f"Suspicious 429: {endpoint}")
    return response

def lambda_handler(event, context):
    httpContext = event["requestContext"]["http"]
    method = httpContext["method"]
    path = httpContext["path"]
    endpoint = f"{method} {path}"
    headers = event["headers"]
    original_host = headers["host"]
    request_rejecting_429 = lambda: reject_429(
        requests.request(
            method=method,
            headers={**headers, "Host": to_retryable_host(original_host)},
            url=to_retryable_url(original_host, path),
            params=event.get("queryStringParameters", None),
            data=event.get("body", None)
        ),
        endpoint
    )
    
    max_sleep = datetime.timedelta(seconds=10)
    try:
        response = avereno.retry(
            request_rejecting_429,
            max_sleep=max_sleep,
            on_retry=lambda current_nb_retries, current_error: logger.error(
                f"Retry no.{current_nb_retries} after error: {current_error}"
            ),
        )
        return {
            "statusCode": response.status_code,
            "body": response.content
        }
    except avereno.GiveUpRetryError:
        error_message = f"GiveUpRetryError after max_sleep={max_sleep}: {endpoint}"
        logger.error(error_message)
        return {
            "statusCode": 500,
            "body": error_message
        }
