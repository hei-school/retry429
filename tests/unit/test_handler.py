import pytest
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

@responses.activate
def test_ping_is_unknown(apigw_ping_event):
    response = app.lambda_handler(apigw_ping_event, "")

    assert response["statusCode"] == 500
    assert "GiveUpRetryError" in response["body"]

@responses.activate
def test_ping_is_eventually_known(apigw_ping_event):
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
        status=200)

    response = app.lambda_handler(apigw_ping_event, "")

    assert response["statusCode"] == 200

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