import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Union
from urllib.parse import quote

import git
import requests


def add_credentials(url: str, token: str) -> Union[str, None]:
    """Adding credentials to the URL for git operations.

    For Bitbucket API tokens (starting with ATAT), uses the static username
    'x-bitbucket-api-token-auth' as recommended by Bitbucket.
    URL may contain existing credentials which will be replaced.

    Args:
        url (str): source url
        token (str): API token

    Returns:
        str: url with credentials, None if invalid url
    """
    if "@" in url:
        repo = url.split("@")[1]
    elif "//" in url:
        repo = url.split("//")[1]
    else:
        print(f"Invalid URL: {url}")
        return None

    # For Bitbucket API tokens, use the static username as per Bitbucket documentation
    username = "x-bitbucket-api-token-auth"

    # URL-encode the token to handle special characters
    encoded_token = quote(token, safe="")
    return "https://" + username + ":" + encoded_token + "@" + repo


def _process_repo(
    repo_name: str, repo_url: str, workspace: str, skip_existing: bool, refresh: bool
) -> None:
    """Process a single repository cloning or pulling changes.

    Args:
        repo (str): repository name
        config (BucketClonerConfig): configuration dataclass
    """
    if Path(f"{workspace}/{repo_name}").exists():
        if skip_existing:
            print(f"Skipping {workspace}/{repo_name} because it already exists.")
            return

        if refresh:
            print(f"Pulling changes for {workspace}/{repo_name}.")
            local_repo = git.Repo(f"{workspace}/{repo_name}")
            origin = local_repo.remotes.origin
            origin.pull()
            return

        print(f"Deleting {workspace}/{repo_name} because it already exists.")
        try:
            shutil.rmtree(f"{workspace}/{repo_name}")
        except PermissionError as e:
            print(f"Error deleting {workspace}/{repo_name}: {e}\nSkipping.")
            return

    git.Repo.clone_from(repo_url, f"{workspace}/{repo_name}")


def _clone_bitbucket_workspace(
    email: str,
    token: str,
    workspace: str,
    skip_existing: bool,
    project: Optional[str],
    refresh: bool,
) -> None:
    """Cloning all repositories

    Args:
        email (str): account email
        token (str): API token
    """

    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}?pagelen=10"
    if project:
        url = url + f"&q=project.key%3D%22{project}%22"

    while (
        resp := requests.get(url, auth=(email, token), timeout=10)
    ).status_code == requests.codes.OK:
        jresp = resp.json()

        for repo in jresp["values"]:
            if repo["scm"] == "git":
                # Checking if there is a https clone link
                repo_url = None
                for clone in repo["links"]["clone"]:
                    if clone["name"] == "https":
                        repo_url = clone["href"]
                        break

                if repo_url is None:
                    print(
                        f"Skipping {repo['name']} because there is no https clone link."
                    )
                    continue

                repo_url = add_credentials(repo_url, token)
                _process_repo(repo["name"], repo_url, workspace, skip_existing, refresh)

            else:
                print(
                    f"Skipping {repo['name']} because it is not a git but a {repo['scm']} repository."
                )

        if "next" not in resp.json():
            break
        url = resp.json()["next"]
    else:
        print(f"The url {url} returned status code {resp.status_code}.")


def clone_bitbucket(
    email: str,
    token: str,
    workspaces: Optional[str],
    skip_existing: bool,
    project: Optional[str],
    refresh: bool,
) -> None:
    """Cloning all repositories

    Args:
        email (str): account email
        token (str): API token
        workspaces (str | None): workspace name
        skip_existing (bool): skip existing repositories
    """
    if workspaces is None:
        workspaces = [w["slug"] for w in list_bitbucket_workspaces(email, token)]
    else:
        workspaces = workspaces.split(",")

    for workspace in workspaces:
        if not Path(workspace).exists():
            Path(workspace).mkdir()
        _clone_bitbucket_workspace(
            email, token, workspace, skip_existing, project, refresh
        )


def list_bitbucket_workspaces(email: str, token: str) -> list:
    """List all workspaces

    Args:
        email (str): account email
        token (str): API token

    Returns:
        list: List of workspaces (dict with name, slug, and url as entries)
    """
    url = "https://api.bitbucket.org/2.0/workspaces"

    workspaces = []

    while (
        resp := requests.get(url, auth=(email, token), timeout=10)
    ).status_code == requests.codes.OK:
        jresp = resp.json()

        for workspace in jresp["values"]:
            w = {
                "name": workspace["name"],
                "slug": workspace["slug"],
                "url": workspace["links"]["html"]["href"],
            }
            workspaces.append(w)

        if "next" not in resp.json():
            break
        url = resp.json()["next"]

    else:
        print(f"The url {url} returned status code {resp.status_code}.")

    return workspaces


def main(args: List[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", help="Account email", required=True)
    parser.add_argument("-t", "--token", help="API token", required=True)
    parser.add_argument(
        "-w", "--workspace", help="Workspace name(s), separated by comma"
    )
    parser.add_argument(
        "-s", "--skip-existing", help="Skip existing repositories", action="store_true"
    )
    parser.add_argument(
        "--project", help="Limit the clone to a specifc bitbucket project"
    )
    parser.add_argument("command", help="Command", choices=["clone", "workspace"])
    parser.add_argument(
        "-r",
        "--refresh",
        help="Pulls changes if the repository exists",
        action="store_true",
    )

    namespace = parser.parse_args(args)

    if namespace.command == "clone":
        clone_bitbucket(
            namespace.email,
            namespace.token,
            namespace.workspace,
            namespace.skip_existing,
            namespace.project,
            namespace.refresh,
        )

    elif namespace.command == "workspace":
        workspaces = list_bitbucket_workspaces(namespace.email, namespace.token)
        for w in workspaces:
            print(f"{w['name']} ({w['slug']}) - {w['url']}")


def entry_point() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    entry_point()
