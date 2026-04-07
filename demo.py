import asyncio
from rich.console import Console

console = Console()


async def main():
    console.print("[bold cyan]KAIROS demo[/bold cyan]\n")

    # 1. terminal nudge
    console.print("[bold]1. Terminal nudge[/bold]")
    from actions import print_brief
    print_brief("3 unresolved TODOs found in agent/tools.py")

    # 2. desktop notification
    console.print("\n[bold]2. Desktop notification[/bold]")
    from actions import notify
    notify("KAIROS: stale PR open for 6 days with no review")

    # 3. github pr comment
    console.print("\n[bold]3. GitHub PR comment[/bold]")
    from actions import post_pr_comment
    from config import GITHUB_REPO
    from github import Github
    from config import GITHUB_TOKEN

    # create a draft PR to comment on
    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(GITHUB_REPO)

        # create a test branch
        main_sha = repo.get_branch("main").commit.sha
        try:
            repo.create_git_ref("refs/heads/kairos-demo", main_sha)
            console.print("  created branch kairos-demo")
        except Exception:
            console.print("  branch already exists, reusing")

        # open a PR
        try:
            pr = repo.create_pull(
                title="[KAIROS demo] test PR for notification",
                body="This PR was created by the KAIROS demo script to test PR comment notifications.",
                head="kairos-demo",
                base="main",
            )
            console.print(f"  opened PR #{pr.number}")
            post_pr_comment(pr.number, "TODOs found in `agent/tools.py` — consider implementing tool calling before next release.")
            console.print(f"  posted comment on PR #{pr.number}")
            console.print(f"  [dim]https://github.com/{GITHUB_REPO}/pull/{pr.number}[/dim]")
        except Exception as e:
            console.print(f"  [yellow]PR already exists or error: {e}[/yellow]")
    except Exception as e:
        console.print(f"  [red]GitHub error: {e}[/red]")

    console.print("\n[bold]done.[/bold]")


if __name__ == "__main__":
    asyncio.run(main())
