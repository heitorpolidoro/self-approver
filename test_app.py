"""This file contains test cases for the Pull Request Generator application."""
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
import sentry_sdk

from app import app, approve_if_ok, approve_if_ok_pr


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
    return commit


@pytest.fixture
def repository(protected_branch, branch, commit):
    """
    This fixture returns a mocked repository object with default values for the attributes.
    :return: Mocked Repository
    """
    repository = Mock(
        default_branch="master", full_name="heitorpolidoro/pull-request-generator"
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


@pytest.fixture
def mock_approve_if_ok_pr():
    with patch("app.approve_if_ok_pr") as mock:
        mock.return_value = None
        yield mock


def test_approve_if_ok_success(
    event, repository, pull, protected_branch, mock_approve_if_ok_pr, capsys
):
    approve_if_ok(event)
    mock_approve_if_ok_pr.assert_called_once_with(repository, pull, protected_branch)
    out, _ = capsys.readouterr()
    assert "Pull Request #1 approved" in out


def test_approve_if_ok_approved(
    event, repository, pull, protected_branch, mock_approve_if_ok_pr, capsys
):
    pull.state = "approved"
    approve_if_ok(event)
    mock_approve_if_ok_pr.assert_not_called()
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 approved" in out


def test_approve_if_ok_closed_pr(
    event, repository, pull, branch, mock_approve_if_ok_pr, capsys
):
    pull.state = "closed"
    approve_if_ok(event)
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 closed" in out


def test_approve_if_ok_not_protected_branch(
    event, repository, pull, branch, mock_approve_if_ok_pr, capsys
):
    pull.base = branch
    approve_if_ok(event)
    mock_approve_if_ok_pr.assert_not_called()
    out, _ = capsys.readouterr()
    assert "Not approving - Pull Request #1 base branch not protected" in out


def test_approve_if_ok_pr(pull, repository, protected_branch):
    assert approve_if_ok_pr(repository, pull, protected_branch) is None
    pull.create_review.assert_called_once_with(
        body="Approved by Self Approver", event="APPROVE"
    )


def test_approve_if_ok_pr_dismissed_review(pull, repository, protected_branch, author):
    pull.requested_reviewers = []
    pull.get_reviews.return_value = [
        Mock(state="DISMISSED", user=author),
        Mock(state="COMMENTED", user=Mock(login="other")),
    ]
    assert approve_if_ok_pr(repository, pull, protected_branch) is None
    pull.create_review.assert_called_once_with(
        body="Approved by Self Approver", event="APPROVE"
    )


def test_approve_if_ok_pr_wrong_review_count(
    pull, repository, protected_branch, author
):
    required_pull_request_reviews = (
        protected_branch.get_protection.return_value.required_pull_request_reviews
    )

    required_pull_request_reviews.required_approving_review_count = 2
    required_pull_request_reviews.require_code_owner_reviews = [author]
    assert "Wrong required approving review count: 2" == approve_if_ok_pr(
        repository, pull, protected_branch
    )

    pull.create_review.assert_not_called()


def test_approve_if_ok_pr_without_requested_review(
    pull, repository, protected_branch, author
):
    required_pull_request_reviews = (
        protected_branch.get_protection.return_value.required_pull_request_reviews
    )
    required_pull_request_reviews.required_approving_review_count = 1
    required_pull_request_reviews.require_code_owner_reviews = [author]
    pull.requested_reviewers = []
    assert (
        f"Pull Request #1 branch owner '{author.login}' not in requested reviewers"
        == approve_if_ok_pr(repository, pull, protected_branch)
    )

    pull.create_review.assert_not_called()


def test_approve_if_ok_pr_requested_review_other_author(
    pull, repository, protected_branch, author
):
    required_pull_request_reviews = (
        protected_branch.get_protection.return_value.required_pull_request_reviews
    )
    other_author = Mock(login="other")
    required_pull_request_reviews.required_approving_review_count = 1
    required_pull_request_reviews.require_code_owner_reviews = [author]
    pull.requested_reviewers = [other_author]
    assert (
        f"Pull Request #1 branch owner '{author.login}' not in requested reviewers"
        == approve_if_ok_pr(repository, pull, protected_branch)
    )

    pull.create_review.assert_not_called()


def test_approve_if_ok_pr_dismissed_other_author(
    pull, repository, protected_branch, author
):
    pull.requested_reviewers = []
    other_author = Mock(login="other")
    pull.get_reviews.return_value = [Mock(state="DISMISSED", user=other_author)]
    assert (
        f"Pull Request #1 branch owner '{author.login}' not in requested reviewers"
        == approve_if_ok_pr(repository, pull, protected_branch)
    )

    pull.create_review.assert_not_called()


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
