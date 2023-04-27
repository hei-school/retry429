import pytest
from unittest import TestCase, mock
import os
import json
import responses
from responses import matchers

from retry_429 import app

def read_filepath_content(filepath):
    with open(filepath, "r") as json_file:
        return json.loads(json_file.read())

@pytest.fixture()
def apigw_ping_event():
    return read_filepath_content("./events/ping.json")

@pytest.fixture()
def apigw_post_non_b64_event():
    return read_filepath_content("./events/post_non_b64.json")

@pytest.fixture()
def apigw_post_b64_event():
    return read_filepath_content("./events/post_b64.json")

@pytest.fixture()
def apigw_get_with_query_params_event():
    return read_filepath_content("./events/get_with_query_params.json")

@pytest.fixture()
def apigw_get_with_two_headers_event():
    return read_filepath_content("./events/get_with_two_headers.json")

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_ping(apigw_ping_event):
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/ping",
        body="pong",
        status=200)

    response = app.lambda_handler(apigw_ping_event, "")

    assert response["statusCode"] == 200
    assert response["isBase64Encoded"]  == True
    assert response["body"]  == "cG9uZw==" # "pong", for non-base64 fluent folks

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_ping_is_unknown(apigw_ping_event):
    response = app.lambda_handler(apigw_ping_event, "")

    assert response["statusCode"] == 500
    assert "GiveUpRetryError" in response["body"]

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "internal-<original_host>", "TARGET_PROTOCOL": "https" })
@responses.activate
def test_ping_is_eventually_known(apigw_ping_event):
    # 1 try
    responses.add(
        responses.GET,
        "https://internal-api-preprod.bpartners.app/ping",
        status=429)
    # 3 retries
    responses.add(
        responses.GET,
        "https://internal-api-preprod.bpartners.app/ping",
        status=429)
    responses.add(
        responses.GET,
        "https://internal-api-preprod.bpartners.app/ping",
        status=429)
    responses.add(
        responses.GET,
        "https://internal-api-preprod.bpartners.app/ping",
        status=200)

    response = app.lambda_handler(apigw_ping_event, "")

    assert response["statusCode"] == 200

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_ping_is_known_too_late(apigw_ping_event):
    # 1 try
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/ping",
        status=429)
    # 3 retries
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/ping",
        status=429)
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/ping",
        status=429)
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/ping",
        status=429)
    # 4-th retry that is never done...
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/ping",
        body="pong",
        status=200)

    response = app.lambda_handler(apigw_ping_event, "")

    assert response["statusCode"] == 500
    assert "GiveUpRetryError" in response["body"]

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_post_non_b64(apigw_post_non_b64_event):
    responses.add(
        responses.POST,
        "http://private-api-preprod.bpartners.app/thepath",
        match=[
            matchers.json_params_matcher({ "foo": "bar €" })
        ],
        status=200)

    response = app.lambda_handler(apigw_post_non_b64_event, "")

    assert response["statusCode"] == 200

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_post_b64(apigw_post_b64_event):
    responses.add(
        responses.POST,
        "http://private-api-preprod.bpartners.app/thepath",
        match=[
            matchers.json_params_matcher({ "foo": "bar €" })
        ],
        status=200)

    response = app.lambda_handler(apigw_post_b64_event, "")

    assert response["statusCode"] == 200

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_query_params_are_forwarded(apigw_get_with_query_params_event):
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/thepath?param1=value1",
        status=200)

    response = app.lambda_handler(apigw_get_with_query_params_event, "")

    assert response["statusCode"] == 200

@mock.patch.dict(os.environ, { "TARGET_HOST_TEMPLATE": "private-<original_host>", "TARGET_PROTOCOL": "http" })
@responses.activate
def test_headers_are_forwarded(apigw_get_with_two_headers_event):
    responses.add(
        responses.GET,
        "http://private-api-preprod.bpartners.app/thepath?param1=value1",
        match=[
            matchers.header_matcher({
                "host": "private-api-preprod.bpartners.app",
                "user-agent": "Mozilla/5.0"
            })
        ],
        status=200,
        headers={"A-Response-Header": "a header value"}
    )

    response = app.lambda_handler(apigw_get_with_two_headers_event, "")

    assert response["statusCode"] == 200
    assert response["headers"] == {
        "A-Response-Header": "a header value",
        # content-type is always text as we systematically encode to base64
        "Content-Type": "text/plain"
    }