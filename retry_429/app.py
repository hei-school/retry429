import requests
import json
import avereno
import logging
import datetime
import base64

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

def reject_429(response, host, endpoint):
    if response.status_code == 429:
        raise Exception(f"Definite 429: {host}, {endpoint}")
    if response.status_code == 500:
        raise Exception(f"Suspicious 500: {host}, {endpoint}")
    return response

def to_base64(content):
    return base64.b64encode(content).decode()

def lambda_handler(event, context):
    httpContext = event["requestContext"]["http"]
    method = httpContext["method"]
    path = httpContext["path"]
    endpoint = f"{method} {path}"
    headers = event["headers"]
    payload = event.get("body", None)
    utf8_payload = None if payload is None else payload.encode("utf-8")

    original_host = headers["host"]
    retryable_host = to_retryable_host(original_host)
    request_rejecting_429 = lambda: reject_429(
        requests.request(
            method=method,
            headers={**headers, "Host": retryable_host},
            url=to_retryable_url(original_host, path),
            params=event.get("queryStringParameters", None),
            data=utf8_payload
        ),
        retryable_host,
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
            "body": to_base64(response.content),
            "isBase64Encoded": True
        }
    except avereno.GiveUpRetryError:
        error_message = f"GiveUpRetryError after max_sleep={max_sleep}: {retryable_host}, {endpoint}"
        logger.error(error_message)
        return {
            "statusCode": 500,
            "body": error_message
        }
