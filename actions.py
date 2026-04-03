from github import Github
from plyer import notification
from rich.console import Console

from config import GITHUB_REPO, GITHUB_TOKEN

console = Console()


def print_brief(message: str):
    console.print(f"[dim]KAIROS[/dim] [white]{message}[/white]")


def notify(message: str):
    try:
        notification.notify(
            app_name="KAIROS",
            title="KAIROS",
            message=message[:100],
            timeout=10,
        )
    except Exception:
        print_brief(message)


def post_pr_comment(pr_number: int, message: str):
    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(f"**KAIROS:** {message}")
    except Exception as e:
        print_brief(f"Failed to post PR comment: {e}")
