import pytest
import responses
from retry_429 import app
import json

def read_filepath_content(filepath):
    with open(filepath, "r") as json_file:
        return json.loads(json_file.read())

@pytest.fixture()
def apigw_ping_event():
    return read_filepath_content("./events/ping.json")

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
