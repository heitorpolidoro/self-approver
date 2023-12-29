"""
This file contains the main application logic for the Pull Request Generator,
including a webhook handler for creating pull requests when new branches are created.
"""
import logging
import os
import sys

import sentry_sdk
from flask import Flask, request
from githubapp import webhook_handler
from githubapp.events import StatusEvent

app = Flask("Self Approver")
app.__doc__ = "This is a Flask application auto merging pull requests."

if sentry_dns := os.getenv("SENTRY_DNS"):  # pragma: no cover
    # Initialize Sentry SDK for error logging
    sentry_sdk.init(sentry_dns)

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    format="%(levelname)s:%(module)s:%(funcName)s:%(message)s",
    level=logging.INFO,
)


# @app.route("/callback", methods=["GET"])
# def callback():
#     installation_id from query string
#     headers = dict(request.headers)
#     body = request.json


@webhook_handler.webhook_handler(StatusEvent)
def approve_if_ok(event: StatusEvent) -> None:
    """
    This function is a webhook handler that check if the state is "success" and if the base branch of
    each PR is protected, if so try to approve the PR

    :param event: The status event
    """
    repository = event.repository
    if event.state == "success":
        for pr in event.commit.get_pulls():
            base = repository.get_branch(pr.base.ref)
            if base.protected:
                approve_if_ok_pr(repository, pr, base)


def approve_if_ok_pr(repository, pr, base):
    """
    This function checks if the protection rules matches:
    - Has only one required review
    - The branch creator is the same as the requested review

    :param repository:
    :param pr:
    :param base:
    """
    protection = base.get_protection()
    if (
        protection.required_pull_request_reviews.require_code_owner_reviews
        and protection.required_pull_request_reviews.required_approving_review_count
        == 1
    ):
        head = repository.get_branch(pr.head.ref)
        branch_owner = (
            repository.compare(base.commit.sha, head.commit.sha).commits[0].author
        )
        if pr.requested_reviewers == [branch_owner]:
            pr.create_review(event="APPROVE", body="Approved by Self Approver")


@app.route("/", methods=["GET"])
def root() -> str:
    """
    This route displays the welcome screen of the application.
    It uses the root function of the webhook_handler to generate the welcome screen.
    """
    return webhook_handler.root(app.name)()


@app.route("/", methods=["POST"])
def webhook() -> str:
    """
    This route is the endpoint that receives the GitHub webhook call.
    It handles the headers and body of the request, and passes them to the webhook_handler for processing.
    """
    headers = dict(request.headers)
    body = request.json
    webhook_handler.handle(headers, body)
    return "OK"
