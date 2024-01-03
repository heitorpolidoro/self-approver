"""This file contains test cases for the Pull Request Generator application."""
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
import sentry_sdk

from app import app, approve


@pytest.fixture
def branch():
    """
    This fixture returns a mocked branch object with default values for the attributes.
    :return: Mocked Repository
    """
    return Mock(protected=False, ref="feature")


@pytest.fixture
def author():
    """
    This fixture returns a mocked author object with default values for the attributes.
    :return: Mocked NamedUser
    """
    return Mock(login="heitorpolidoro")


@pytest.fixture
def protected_branch(author):
    """
    This fixture returns a mocked protected branch object with default values for the attributes.
    :return: Mocked Repository
    """
    protected_branch = Mock(protected=True, ref="master")

    required_pull_request_reviews = (
        protected_branch.get_protection.return_value.required_pull_request_reviews
    )
    required_pull_request_reviews.require_code_owner_reviews = [author]
    required_pull_request_reviews.required_approving_review_count = 1
    return protected_branch


@pytest.fixture
def pull(protected_branch, branch, author):
    """
    This fixture returns a mocked pull object with default values for the attributes.
    :return: Mocked Repository
    """
    pull = Mock(
        base=protected_branch,
        head=branch,
        requested_reviewers=[author],
        state="open",
        number=1,
    )
    pull.get_reviews.return_value = []
    return pull


@pytest.fixture
def commit(pull, author):
    """
    This fixture returns a mocked commit object with default values for the attributes.
    :return: Mocked Commit
    """
    commit = Mock(author=author)
    commit.get_pulls.return_value = [pull]
    commit.get_check_runs.return_value = [Mock(conclusion="success")]
    return commit


@pytest.fixture
def repository(protected_branch, branch, commit):
    """
    This fixture returns a mocked repository object with default values for the attributes.
    :return: Mocked Repository
    """
    repository = Mock(
        default_branch="master",
        full_name="heitorpolidoro/pull-request-generator",
        owner=Mock(login="heitorpolidoro"),
    )
    repository.get_branch = (
        lambda branch_ref: protected_branch if branch_ref == "master" else branch
    )
    repository.compare.return_value.commits = [commit]
    return repository


@pytest.fixture
def event(repository, commit):
    """
    This fixture returns a mocked event object with default values for the attributes.
    :return: Mocked Event
    """
    return Mock(
        repository=repository,
        commit=commit,
        ref="issue-42",
        branches=[Mock(name="issue-42")],
    )


def test_approve_success(event, pull, capsys):
    approve(event)
    pull.create_review.assert_called_once_with(
        body="Approved by Self Approver", event="APPROVE"
    )
    out, _ = capsys.readouterr()
    assert "Pull Request #1 approved" in out


def test_not_approve_when_other_owner(event, pull, repository, capsys):
    repository.owner = Mock(login="other")
    approve(event)
    pull.create_review.assert_not_called()
    out, _ = capsys.readouterr()
    assert (
        'Not approving - The branch "feature" owner, "heitorpolidoro", is not the same as the repository owner, "other"'
        in out
    )


def test_not_approve_when_base_not_protected(event, pull, branch, capsys):
    pull.base = branch
    approve(event)
    pull.create_review.assert_not_called()
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 base branch not protected" in out


def test_not_approve_when_already_approved(event, pull, author, capsys):
    pull.get_reviews.return_value = [
        Mock(state="APPROVED", user=author),
    ]
    approve(event)
    pull.create_review.assert_not_called()
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 already approved" in out


def test_not_approve_when_pr_not_open(event, pull, author, capsys):
    pull.state = "closed"
    approve(event)
    pull.create_review.assert_not_called()
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 closed" in out


def test_not_approve_when_failing_checks(event, pull, commit, capsys):
    commit.get_check_runs.return_value = [Mock(state="pending")]
    approve(event)
    pull.create_review.assert_not_called()
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 not all checks are success" in out


def test_re_approve_when_dismissed(event, pull, author, capsys):
    pull.get_reviews.return_value = [
        Mock(state="DISMISSED", user=author),
    ]
    approve(event)
    pull.create_review.assert_called_once_with(
        body="Approved by Self Approver", event="APPROVE"
    )
    out, _ = capsys.readouterr()
    assert "Pull Request #1 approved" in out


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
