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


# def test_create_pr(event):
#     """
#     This test case tests the create_branch_handler function when there are commits between the new branch and the
#     default branch. It checks that the function creates a pull request with the correct parameters.
#
#     Expected behavior:
#     - The function should create a pull request with the title "feature".
#     - The pull request body should include a link to the issue with the title "feature" and the body "feature body".
#     - The pull request body should include the text "Closes #42".
#     - The pull request should not be a draft.
#
#     """
#     expected_body = """### [feature](https://github.com/heitorpolidoro/pull-request-generator/issues/42)
#
# feature body
#
# Closes #42
#
# """
#     create_branch_handler(event)
#     event.repository.create_pull.assert_called_once_with(
#         "master",
#         "issue-42",
#         title="feature",
#         body=expected_body,
#         draft=False,
#     )
#     event.repository.create_pull.return_value.enable_automerge.assert_called_once_with(
#         merge_method="SQUASH"
#     )
#
#
# def test_create_pr_no_commits(event):
#     """
#     This test case tests the create_branch_handler function when there are no commits between the new branch and the
#     default branch. It checks that the function handles this situation correctly by not creating a pull request.
#     """
#     event.repository.create_pull.side_effect = GithubException(
#         422, message="No commits between 'master' and 'issue-42'"
#     )
#     create_branch_handler(event)
#
#
# def test_create_pr_other_exceptions(event):
#     """
#     This test case tests the create_branch_handler function when an exception other than 'No commits between master and
#     feature' is raised. It checks that the function raises the exception as expected.
#
#     Expected behavior:
#     - The function should raise a GithubException with the message "Other exception".
#
#     """
#     event.repository.create_pull.side_effect = GithubException(
#         422, message="Other exception"
#     )
#     with pytest.raises(GithubException):
#         create_branch_handler(event)
#
#
# def test_enable_just_automerge_on_existing_pr(event):
#     """
#     This test case tests the create_branch_handler function when a pull request already exists for the new branch.
#     It checks that the function enables auto-merge for the existing pull request and does not create a new pull request.
#
#     Expected behavior:
#     - The function should not create a new pull request.
#     - The function should enable auto-merge for the existing pull request with the merge method "SQUASH".
#
#     """
#     existing_pr = Mock()
#     event.repository.get_pulls.return_value = [existing_pr]
#     create_branch_handler(event)
#     event.repository.create_pull.assert_not_called()
#     existing_pr.enable_automerge.assert_called_once_with(merge_method="SQUASH")


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
        assert response.text == "Pull Request Generator App up and running!"

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
