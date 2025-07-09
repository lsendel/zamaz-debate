"""
GitHub App Webhook Server
Handles incoming webhooks from GitHub and dispatches them to appropriate handlers
"""

import os
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zamaz GitHub App Webhook Server")

# Configuration
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")


# Task queue for Claude
class TaskQueue:
    """Simple in-memory task queue (replace with Redis/RabbitMQ in production)"""

    def __init__(self):
        self.tasks = []

    def add_task(self, task: Dict[str, Any]):
        task["created_at"] = datetime.utcnow().isoformat()
        task["status"] = "pending"
        self.tasks.append(task)
        logger.info(f"Added task: {task['type']} for {task.get('issue_number', 'N/A')}")

    def get_pending_tasks(self) -> list:
        return [t for t in self.tasks if t["status"] == "pending"]

    def mark_completed(self, task_id: str):
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.utcnow().isoformat()


task_queue = TaskQueue()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature or not secret:
        return False

    expected_signature = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


class WebhookHandlers:
    """Handles different types of GitHub webhook events"""

    @staticmethod
    async def handle_issue_opened(payload: Dict[str, Any]):
        """Handle new issue creation"""
        issue = payload["issue"]

        # Check if issue has ai-assigned label
        labels = [label["name"] for label in issue.get("labels", [])]
        if "ai-assigned" in labels:
            task_queue.add_task(
                {
                    "id": f"issue-{issue['number']}-{datetime.utcnow().timestamp()}",
                    "type": "implement_issue",
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "issue_body": issue["body"],
                    "issue_url": issue["html_url"],
                    "repository": payload["repository"]["full_name"],
                }
            )
            return {"status": "Task queued for AI implementation"}

        return {"status": "Issue not AI-assigned, skipping"}

    @staticmethod
    async def handle_issue_labeled(payload: Dict[str, Any]):
        """Handle issue labeling"""
        issue = payload["issue"]
        label = payload["label"]["name"]

        if label == "ai-assigned":
            task_queue.add_task(
                {
                    "id": f"issue-{issue['number']}-{datetime.utcnow().timestamp()}",
                    "type": "implement_issue",
                    "issue_number": issue["number"],
                    "issue_title": issue["title"],
                    "issue_body": issue["body"],
                    "issue_url": issue["html_url"],
                    "repository": payload["repository"]["full_name"],
                }
            )
            return {"status": "Task queued for AI implementation"}

        return {"status": f"Label {label} added, no action needed"}

    @staticmethod
    async def handle_issue_comment(payload: Dict[str, Any]):
        """Handle issue comments"""
        issue = payload["issue"]
        comment = payload["comment"]

        # Check for AI mentions
        if "@zamaz-ai" in comment["body"] or "@claude" in comment["body"]:
            task_queue.add_task(
                {
                    "id": f"comment-{comment['id']}-{datetime.utcnow().timestamp()}",
                    "type": "respond_to_comment",
                    "issue_number": issue["number"],
                    "comment_body": comment["body"],
                    "comment_url": comment["html_url"],
                    "repository": payload["repository"]["full_name"],
                }
            )
            return {"status": "Comment task queued for AI response"}

        return {"status": "No AI mention in comment"}

    @staticmethod
    async def handle_pull_request(payload: Dict[str, Any]):
        """Handle pull request events"""
        action = payload["action"]
        pr = payload["pull_request"]

        if action == "opened":
            # Check if PR needs AI review
            labels = [label["name"] for label in pr.get("labels", [])]
            if "ai-review" in labels:
                task_queue.add_task(
                    {
                        "id": f"pr-{pr['number']}-{datetime.utcnow().timestamp()}",
                        "type": "review_pr",
                        "pr_number": pr["number"],
                        "pr_title": pr["title"],
                        "pr_body": pr["body"],
                        "pr_url": pr["html_url"],
                        "repository": payload["repository"]["full_name"],
                    }
                )
                return {"status": "PR queued for AI review"}

        return {"status": f"PR action {action} processed"}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "Zamaz GitHub App Webhook Server",
        "pending_tasks": len(task_queue.get_pending_tasks()),
    }


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
    x_github_delivery: str = Header(None),
):
    """Main webhook endpoint for GitHub events"""

    # Get request body
    body = await request.body()

    # Verify webhook signature
    if GITHUB_WEBHOOK_SECRET:
        if not verify_webhook_signature(body, x_hub_signature_256, GITHUB_WEBHOOK_SECRET):
            logger.warning(f"Invalid webhook signature for delivery {x_github_delivery}")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received {x_github_event} event (delivery: {x_github_delivery})")

    # Route to appropriate handler
    handlers = WebhookHandlers()

    if x_github_event == "issues":
        action = payload.get("action")
        if action == "opened":
            result = await handlers.handle_issue_opened(payload)
        elif action == "labeled":
            result = await handlers.handle_issue_labeled(payload)
        else:
            result = {"status": f"Unhandled issue action: {action}"}

    elif x_github_event == "issue_comment":
        result = await handlers.handle_issue_comment(payload)

    elif x_github_event == "pull_request":
        result = await handlers.handle_pull_request(payload)

    elif x_github_event == "ping":
        result = {"status": "pong"}

    else:
        result = {"status": f"Event {x_github_event} not handled"}

    return JSONResponse(content=result)


@app.get("/tasks/pending")
async def get_pending_tasks():
    """Get all pending tasks for processing"""
    return {"tasks": task_queue.get_pending_tasks()}


@app.post("/tasks/{task_id}/complete")
async def mark_task_complete(task_id: str):
    """Mark a task as completed"""
    task_queue.mark_completed(task_id)
    return {"status": "Task marked as completed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
