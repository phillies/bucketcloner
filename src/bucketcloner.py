import argparse
import os
import shutil
import sys
from typing import Union, List

import git
import requests


def add_credentials(url: str, user: str, password: str) -> Union[str, None]:
    """Adding username and password to the URL.
    URL may contain the username in the form of http(s)://user@example.com
    or just the url http(s)://example.com and will return
    https://user:password@example.com

    Args:
        url (str): source url
        user (str): username
        password (str): password

    Returns:
        str: url with credentials, None if invalid url
    """
    if '@' in url:
        repo = url.split('@')[1]
    elif '//' in url:
        repo = url.split('//')[1]
    else:
        print(f'Invalid URL: {url}')
        return None
    url = 'https://' + user + ':' + password + '@' + repo
    return url


def _clone_bitbucket_workspace(user: str, password: str, workspace: str, skip_existing: bool = True) -> None:
    """Cloning all repositories

    Args:
        user (str): username
        password (str): password
    """
    url = f'https://api.bitbucket.org/2.0/repositories/{workspace}?pagelen=10'

    while (resp := requests.get(url, auth=(user, password))).status_code == 200:
        jresp = resp.json()

        for repo in jresp['values']:
            if repo['scm'] == 'git':

                # Checking if there is a https clone link
                repo_url = None
                for clone in repo['links']['clone']:
                    if clone['name'] == 'https':
                        repo_url = clone['href']
                        break

                if repo_url is None:
                    print(f'Skipping {repo["name"]} because there is no https clone link.')
                    continue

                print(f'Cloning {repo["name"]} from {repo_url} into {workspace}.')
                if os.path.exists(f'{workspace}/{repo["name"]}'):
                    if skip_existing:
                        print(f'Skipping {workspace}/{repo["name"]} because it already exists.')
                        continue
                    else:
                        print(f'Deleting {workspace}/{repo["name"]} because it already exists.')
                        shutil.rmtree(f'{workspace}/{repo["name"]}')
                repo_url = add_credentials(repo_url, user, password)
                git.Repo.clone_from(repo_url, f'{workspace}/{repo["name"]}')

            else:
                print(f'Skipping {repo["name"]} because it is not a git but a {repo["scm"]} repository.')

        if 'next' not in resp.json():
            break
        url = resp.json()['next']
    else:
        print(f'The url {url} returned status code {resp.status_code}.')


def clone_bitbucket(user: str, password: str, workspaces: Union[str, None], skip_existing: bool = True) -> None:
    """Cloning all repositories

    Args:
        user (str): username
        password (str): password
        workspaces (str | None): workspace name
        skip_existing (bool): skip existing repositories
    """
    if workspaces is None:
        workspaces = [w['slug'] for w in list_bitbucket_workspaces(user, password)]
    else:
        workspaces = workspaces.split(',')

    for workspace in workspaces:
        if not os.path.exists(workspace):
            os.mkdir(workspace)
        _clone_bitbucket_workspace(user, password, workspace, skip_existing)


def list_bitbucket_workspaces(user: str, password: str) -> list:
    """List all workspaces

    Args:
        user (str): username
        password (str): password

    Returns:
        list: List of workspaces (dict with name, slug, and url as entries)
    """
    url = "https://api.bitbucket.org/2.0/workspaces"

    workspaces = []

    while (resp := requests.get(url, auth=(user, password))).status_code == 200:
        jresp = resp.json()

        for workspace in jresp['values']:
            w = {
                'name': workspace['name'],
                'slug': workspace['slug'],
                'url': workspace['links']['html']['href']
            }
            workspaces.append(w)

        if 'next' not in resp.json():
            break
        url = resp.json()['next']

    else:
        print(f'The url {url} returned status code {resp.status_code}.')

    return workspaces


def main(args: List[str]):
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user', help='Username', required=True)
    parser.add_argument('-p', '--password', help='App password', required=True)
    parser.add_argument('-w', '--workspace', help='Workspace name(s), separated by comma')
    parser.add_argument('-s', '--skip-existing', help='Skip existing repositories', action='store_true')
    parser.add_argument('command', help='Command', choices=['clone', 'workspace'])

    namespace = parser.parse_args(args)

    if namespace.command == 'clone':
        clone_bitbucket(namespace.user, namespace.password, namespace.workspace, namespace.skip_existing)

    elif namespace.command == 'workspace':
        workspaces = list_bitbucket_workspaces(namespace.user, namespace.password)
        for w in workspaces:
            print(f'{w["name"]} ({w["slug"]}) - {w["url"]}')


def entry_point():
    main(sys.argv[1:])


if __name__ == '__main__':
    entry_point()
