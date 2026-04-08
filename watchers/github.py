from datetime import datetime, timezone

from github import Github

from config import GITHUB_REPO, GITHUB_TOKEN


def _gh_repo():
    return Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)


async def get_open_prs() -> list:
    try:
        repo = _gh_repo()
        result = []
        for pr in repo.get_pulls(state="open"):
            now = datetime.now(timezone.utc)
            days_open = (now - pr.created_at.replace(tzinfo=timezone.utc)).days

            reviews = pr.get_reviews()
            review_states = [r.state for r in reviews]
            if "APPROVED" in review_states:
                review_status = "approved"
            elif "CHANGES_REQUESTED" in review_states:
                review_status = "changes_requested"
            elif review_states:
                review_status = "pending"
            else:
                review_status = "none"

            is_stale = days_open > 5 and review_status == "none"

            try:
                files = pr.get_files()
                diff_lines = []
                for f in files:
                    if f.patch:
                        diff_lines.append(f"--- {f.filename}\n{f.patch[:500]}")
                diff = "\n".join(diff_lines)[:2000]
            except Exception:
                diff = ""

            result.append({
                "number": pr.number,
                "title": pr.title,
                "days_open": days_open,
                "has_conflicts": pr.mergeable is False,
                "review_status": review_status,
                "is_stale": is_stale,
                "diff": diff,
            })
        return result
    except Exception:
        return []


async def get_recent_commits(n: int = 10) -> list:
    try:
        repo = _gh_repo()
        result = []
        for commit in repo.get_commits()[:n]:
            result.append({
                "sha": commit.sha[:7],
                "message": commit.commit.message.strip(),
                "author": commit.commit.author.name,
                "timestamp": commit.commit.author.date.replace(tzinfo=timezone.utc).isoformat(),
            })
        return result
    except Exception:
        return []
