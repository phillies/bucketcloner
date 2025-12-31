import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import quote

import git
import requests


@dataclass
class BucketClonerConfig:
    email: str
    token: str
    skip_existing: bool
    refresh: bool
    clone_into_project_folders: bool
    base_folder: Path


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


def _get_workspaces(
    email: str,
    token: str,
    workspaces: Optional[str],
) -> List[str]:
    """Retrieve all workspace slugs for the given account if none are specified,
    otherwise return a list of the specified workspaces.

    Args:
        email (str): account email
        token (str): API token
        workspaces (str | None): comma-separated workspace slugs or None

    Returns:
        List[str]: List of workspace slugs
    """
    if workspaces is None:
        workspace_list = [w["slug"] for w in list_bitbucket_workspaces(email, token)]
    else:
        workspace_list = workspaces.split(",")
    return workspace_list


def _process_repo(
    repo_name: str,
    repo_url: str,
    skip_existing: bool,
    refresh: bool,
    target_folder: Path,
) -> None:
    """Process a single repository cloning or pulling changes.

    Args:
        repo_name (str): repository name
        repo_url (str): repository URL
        skip_existing (bool): whether to skip existing repositories
        refresh (bool): whether to pull changes for existing repositories
        target_folder (Path): target folder to clone into
    """

    if target_folder.exists():
        if skip_existing:
            print(f"Skipping {repo_name} because it already exists.")
            return

        if refresh:
            print(f"Pulling changes for {repo_name}.")
            local_repo = git.Repo(target_folder)
            origin = local_repo.remotes.origin
            origin.pull()
            return

        print(f"Deleting {repo_name} because it already exists.")
        try:
            shutil.rmtree(target_folder)
        except PermissionError as e:
            print(f"Error deleting {repo_name}: {e}\nSkipping.")
            return

    target_folder.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning {repo_name} into {target_folder}.")
    git.Repo.clone_from(repo_url, target_folder)


def _clone_bitbucket_workspace(
    workspace: str,
    project: Optional[str],
    config: BucketClonerConfig,
) -> None:
    """Cloning all repositories

    Args:
        workspace (str): workspace slug
        project (str | None): project key to limit the clone to
        config (BucketClonerConfig): configuration dataclass
    """

    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}?pagelen=10"
    if project:
        url = url + f"&q=project.key%3D%22{project}%22"

    while (
        resp := requests.get(url, auth=(config.email, config.token), timeout=10)
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

                repo_url = add_credentials(repo_url, config.token)
                if repo_url is None:
                    print(f"Skipping {repo['name']} because of invalid URL.")
                    continue

                repo_name = workspace + "/" + repo["name"]

                target_folder = config.base_folder / workspace
                if config.clone_into_project_folders and repo["project"]:
                    target_folder = target_folder / repo["project"]["key"]
                target_folder = target_folder / repo["name"]

                _process_repo(
                    repo_name,
                    repo_url,
                    config.skip_existing,
                    config.refresh,
                    target_folder,
                )

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
    workspaces: Optional[str],
    project: Optional[str],
    config: BucketClonerConfig,
) -> None:
    """Cloning all repositories

    Args:
        email (str): account email
        token (str): API token
        config (BucketClonerConfig): configuration dataclass
    """
    workspace_list = _get_workspaces(config.email, config.token, workspaces)

    for workspace in workspace_list:
        if not Path(workspace).exists():
            Path(workspace).mkdir()

        _clone_bitbucket_workspace(workspace, project, config)


def get_projects_in_workspace(email: str, token: str, workspace: str) -> List[dict]:
    """Retrieve all projects in a given workspace.

    Args:
        email (str): account email
        token (str): API token
        workspace (str): workspace slug

    Returns:
        List[dict]: List of projects (dict with name, key, and url as entries)
    """
    url = f"https://api.bitbucket.org/2.0/workspaces/{workspace}/projects"
    projects = []
    while (
        resp := requests.get(url, auth=(email, token), timeout=10)
    ).status_code == requests.codes.OK:
        jresp = resp.json()
        for project in jresp["values"]:
            p = {
                "name": project["name"],
                "key": project["key"],
                "url": project["links"]["html"]["href"],
            }
            projects.append(p)
        if "next" not in resp.json():
            break
        url = resp.json()["next"]
    else:
        print(f"The url {url} returned status code {resp.status_code}.")
    return projects


def list_bitbucket_workspaces(email: str, token: str) -> List[Dict[str, str]]:
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
    parser.add_argument(
        "command", help="Command", choices=["clone", "workspace", "project"]
    )
    parser.add_argument(
        "-r",
        "--refresh",
        help="Pulls changes if the repository exists",
        action="store_true",
    )
    parser.add_argument(
        "--project-folders",
        help="Clone repositories into project subfolders inside the workspace folder",
        action="store_true",
    )
    parser.add_argument(
        "--base-folder",
        help="Base folder to clone repositories into (default: current working directory)",
        type=Path,
        default=Path.cwd(),
    )

    namespace = parser.parse_args(args)

    if namespace.command == "clone":
        config = BucketClonerConfig(
            email=namespace.email,
            token=namespace.token,
            skip_existing=namespace.skip_existing,
            refresh=namespace.refresh,
            clone_into_project_folders=namespace.project_folders,
            base_folder=namespace.base_folder,
        )
        clone_bitbucket(
            namespace.workspace,
            namespace.project,
            config,
        )

    elif namespace.command == "workspace":
        workspaces = list_bitbucket_workspaces(namespace.email, namespace.token)
        for w in workspaces:
            print(f"{w['name']} ({w['slug']}) - {w['url']}")

    elif namespace.command == "project":
        workspaces = _get_workspaces(
            namespace.email, namespace.token, namespace.workspace
        )

        for workspace in workspaces:
            projects = get_projects_in_workspace(
                namespace.email, namespace.token, workspace
            )
            print(f"Projects in workspace {workspace}:")
            for project in projects:
                print(f"  {project['name']} ({project['key']}) - {project['url']}")
            if not projects:
                print("  No projects found.")
            print()


def entry_point() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    entry_point()
