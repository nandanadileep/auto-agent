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
    try:
        from plyer import notification
        notification.notify(
            app_name="KAIROS",
            title="KAIROS",
            message="stale PR open for 6 days with no review",
            timeout=10,
        )
        console.print("  notification sent — check top right of your screen")
    except Exception as e:
        console.print(f"  [red]notification failed: {e}[/red]")

    # 3. github pr comment
    console.print("\n[bold]3. GitHub PR comment[/bold]")
    from actions import post_pr_comment
    from config import GITHUB_REPO, GITHUB_TOKEN
    from github import Auth, Github

    try:
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = gh.get_repo(GITHUB_REPO)
        main_sha = repo.get_branch("main").commit.sha

        # create branch if not exists
        try:
            repo.create_git_ref("refs/heads/kairos-demo", main_sha)
            console.print("  created branch kairos-demo")
        except Exception:
            console.print("  branch kairos-demo already exists")

        # push a commit to the branch so GitHub accepts the PR
        try:
            existing = repo.get_contents("kairos-demo.md", ref="kairos-demo")
            repo.update_file(
                "kairos-demo.md",
                "kairos demo update",
                "KAIROS demo branch — safe to delete.",
                existing.sha,
                branch="kairos-demo",
            )
        except Exception:
            repo.create_file(
                "kairos-demo.md",
                "kairos demo commit",
                "KAIROS demo branch — safe to delete.",
                branch="kairos-demo",
            )
        console.print("  pushed commit to kairos-demo")

        # open PR
        try:
            pr = repo.create_pull(
                title="[KAIROS demo] test PR",
                body="Created by KAIROS demo script to test PR comment feature.",
                head="kairos-demo",
                base="main",
            )
            console.print(f"  opened PR #{pr.number}")
        except Exception:
            # PR already open, find it
            prs = list(repo.get_pulls(state="open", head=f"{repo.owner.login}:kairos-demo"))
            if prs:
                pr = prs[0]
                console.print(f"  using existing PR #{pr.number}")
            else:
                raise Exception("could not find or create PR")

        post_pr_comment(pr.number, "TODOs found in `agent/tools.py` — implement tool calling before next release.")
        console.print(f"  posted comment on PR #{pr.number}")
        console.print(f"  [dim]https://github.com/{GITHUB_REPO}/pull/{pr.number}[/dim]")

    except Exception as e:
        console.print(f"  [red]GitHub error: {e}[/red]")

    console.print("\n[bold]done.[/bold]")


if __name__ == "__main__":
    asyncio.run(main())
