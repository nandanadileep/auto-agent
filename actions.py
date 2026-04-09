from github import Github
from plyer import notification
from rich.console import Console

from config import GITHUB_REPO, GITHUB_TOKEN

console = Console()


def print_brief(message: str):
    console.print(f"[dim]auto-agent[/dim] [white]{message}[/white]")


def notify(message: str):
    try:
        notification.notify(
            app_name="auto-agent",
            title="auto-agent",
            message=message[:100],
            timeout=10,
        )
    except Exception:
        print_brief(message)


def post_pr_comment(pr_number: int, message: str) -> bool:
    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(f"**auto-agent:** {message}")
        return True
    except Exception as e:
        print_brief(f"Failed to post PR comment: {e}")
        return False
