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

logging.basicConfig(
    stream=sys.stdout,
    format="%(levelname)s:%(module)s:%(funcName)s:%(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

if sentry_dns := os.getenv("SENTRY_DSN"):  # pragma: no cover
    # Initialize Sentry SDK for error logging
    sentry_sdk.init(
        dsn=sentry_dns,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )
    logger.info("Sentry initialized")

app = Flask("Self Approver")
app.__doc__ = "This is a Flask application to automatically approve Pull Requests."


# @app.route("/callback", methods=["GET"])
# def callback():
#     installation_id from query string
#     headers = dict(request.headers)
#     body = request.json


@webhook_handler.webhook_handler(StatusEvent)
def approve(event: StatusEvent) -> None:
    """
    This function is a webhook handler that check if the state is "success" and if the base branch of
    each PR is protected, if so try to approve the PR

    :param event: The status event
    """
    repository = event.repository
    print(f"{repository.full_name}:{[b.name for b in event.branches]}")
    reasons = []
    approved_prs = []
    for pr in event.commit.get_pulls():
        if pr.state != "open":
            reasons.append(f"Pull Request #{pr.number} {pr.state}")
            continue

        base = repository.get_branch(pr.base.ref)
        if not base.protected:
            reasons.append(f"Pull Request #{pr.number} base branch not protected")
            continue

        head = repository.get_branch(pr.head.ref)

        branch_owner = (
            repository.compare(base.commit.sha, head.commit.sha).commits[0].author
        )
        if branch_owner.login != repository.owner.login:
            reasons.append(
                f'The branch "{head.ref}" owner, "{branch_owner.login}", '
                f'is not the same as the repository owner, "{repository.owner.login}"'
            )
            continue

        if any(
            review.user.login == branch_owner.login and review.state == "APPROVED"
            for review in pr.get_reviews()
        ):
            reasons.append(f"Pull Request #{pr.number} already approved")
            continue
        pr.create_review(event="APPROVE", body="Approved by Self Approver")
        approved_prs.append(pr)

    for reason in reasons:
        print(f"Not approving - {reason}")
    for pr in approved_prs:
        print(f"Pull Request #{pr.number} approved")


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
