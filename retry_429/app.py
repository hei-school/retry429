import requests
import urllib3.util.url as urllib3_url
import json
import avereno
import logging
import datetime
import base64
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def to_retryable_host(original_host):
    TargetHostTemplate = os.environ["TargetHostTemplate"]
    return TargetHostTemplate.replace("<original_host>", original_host)

def to_retryable_url(original_host, path):
    protocol = os.environ["TargetProtocol"]
    return f"{protocol}://{to_retryable_host(original_host)}{path}"

def reject_bad_http_statuses(response, host, endpoint):
    RetriedHttpStatuses = os.environ.get("RetriedHttpStatuses", "")
    if str(response.status_code) in RetriedHttpStatuses:
        raise Exception(f"Rejected {response.status_code}: {host}, {endpoint}")
    return response

def to_base64(content):
    return base64.b64encode(content).decode()

def case_insensitive_obj_to_serializable_dict(obj):
    return json.loads(json.dumps(dict(obj)))

def encoded_payload_from_event(event):
    payload = event.get("body", None)
    if payload is None:
        return None
    elif event.get("isBase64Encoded", False):
        return base64.b64decode(payload)
    else:
        return payload.encode("utf-8")

def lambda_handler(event, context):
    httpContext = event["requestContext"]["http"]
    method = httpContext["method"]
    path = httpContext["path"]
    endpoint = f"{method} {path}"
    headers = event["headers"]
    original_host = headers["host"]
    retryable_host = to_retryable_host(original_host)
    params_str = "&".join(
        "%s=%s" % (k,v) for k,v in event.get("queryStringParameters", {}).items())
    urllib3_url._encode_invalid_chars = lambda component, _allowed_chars: component
    request_rejecting_bad_http_statuses = lambda: reject_bad_http_statuses(
        requests.request(
            method=method,
            headers={**headers, "host": retryable_host},
            url=to_retryable_url(original_host, path),
            params=params_str,
            data=encoded_payload_from_event(event)
        ),
        retryable_host,
        endpoint
    )

    max_sleep = datetime.timedelta(seconds=10)
    try:
        response = avereno.retry(
            request_rejecting_bad_http_statuses,
            max_sleep=max_sleep,
            on_retry=lambda current_nb_retries, current_error: logger.error(
                f"Retry no.{current_nb_retries} after error: {current_error}"
            ),
        )
        return {
            "statusCode": response.status_code,
            "body": to_base64(response.content),
            "headers": case_insensitive_obj_to_serializable_dict(response.headers),
            "isBase64Encoded": True
        }
    except avereno.GiveUpRetryError:
        error_message = f"GiveUpRetryError after max_sleep={max_sleep}: {retryable_host}, {endpoint}"
        logger.error(error_message)
        return {
            "statusCode": 500,
            "body": error_message
        }
