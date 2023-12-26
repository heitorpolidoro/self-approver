"""
This file contains the main application logic for the Pull Request Generator,
including a webhook handler for creating pull requests when new branches are created.
"""
import logging
import os
import sys
from typing import Optional

import sentry_sdk
from flask import Flask, request
from github.PullRequest import PullRequest
from github.Repository import Repository
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

def get_existing_pr(repo: Repository, head: str) -> Optional[PullRequest]:  # TODO use from githubapp
    """
    Returns an existing PR if it exists.
    :param repo: The Repository to get the PR from.
    :param head: The branch to check for an existing PR.
    :return: Exists PR or None.
    """
    return next(iter(repo.get_pulls(state="open", head=head)), None)
@webhook_handler.webhook_handler(StatusEvent)
def approve_if_ok(event: StatusEvent) -> None:
    """
    This function is a webhook handler that creates a pull request when a new branch is created.
    It takes a CreateBranchEvent object as a parameter, which contains information about the new branch.
    If a pull request already exists for the new branch, the function enables auto-merge for the pull request.
    Otherwise, it creates a new pull request and enables auto-merge for it.
    """
    if event.state == "success":
        for branch in event.branches:
            pr = get_existing_pr(event.repository, f"{event.repository.owner.login}:{branch}")
            pr.merge(merge_method="SQUASH")


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
