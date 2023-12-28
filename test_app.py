"""This file contains test cases for the Pull Request Generator application."""
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
import sentry_sdk
from github import GithubException

from app import app


@pytest.fixture
def repository():
    """
    This fixture returns a mock repository object with default values for the attributes.
    :return: Mocked Repository
    """
    repository = Mock()
    repository.default_branch = "master"
    repository.full_name = "heitorpolidoro/pull-request-generator"
    repository.get_pulls.return_value = []
    return repository


@pytest.fixture
def issue():
    """
    This fixture returns a mock issue object with default values for the attributes.
    :return: Mocked Issue
    """
    issue = Mock()
    issue.title = "feature"
    issue.body = "feature body"
    issue.number = 42
    return issue


@pytest.fixture
def event(repository, issue):
    """
    This fixture returns a mock event object with default values for the attributes.
    :return: Mocked Event
    """
    event = Mock()
    event.repository = repository
    event.repository.get_issue.return_value = issue
    event.ref = "issue-42"
    return event


class TestApp(TestCase):
    def setUp(self):
        self.app = app.test_client()

    def tearDown(self):
        sentry_sdk.flush()

    def test_root(self):
        """
        Test the root endpoint of the application.
        This test ensures that the root endpoint ("/") of the application is working correctly.
        It sends a GET request to the root endpoint and checks that the response status code is 200 and the response
        text is "Pull Request Generator App up and running!".
        """
        response = self.app.get("/")
        assert response.status_code == 200
        assert response.text == "Self Approver App up and running!"

    def test_webhook(self):
        """
        Test the webhook handler of the application.
        This test ensures that the webhook handler is working correctly.
        It mocks the `handle` function of the `webhook_handler` module, sends a POST request to the root endpoint ("/")
        with a specific JSON payload and headers, and checks that the `handle` function is called with the correct
        arguments.
        """
        with patch("app.webhook_handler.handle") as mock_handle:
            request_json = {"action": "opened", "number": 1}
            headers = {
                "User-Agent": "Werkzeug/3.0.1",
                "Host": "localhost",
                "Content-Type": "application/json",
                "Content-Length": "33",
                "X-Github-Event": "pull_request",
            }
            self.app.post("/", headers=headers, json=request_json)
            mock_handle.assert_called_once_with(headers, request_json)
