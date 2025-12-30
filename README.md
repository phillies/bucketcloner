# Bucketcloner
Simple tool to list all your bitbucket workspaces and clone (all) repositories associated with these workspaces.

## Requirements
1. You need to know your Bitbucket account email. Can be found at https://bitbucket.org/account/settings/email/.
2. You need to create an API token here https://id.atlassian.com/manage-profile/security/api-tokens with read permissions for *account*, *workspace membership* and *repositories*.

Install bucketcloner either by cloning this repository and running `pip install .` or by installing it via `pip install bucketcloner`. Minimum required python version is 3.9.

Alternatively, you can run bucketcloner using `uvx`: `uvx bucketcloner --help`

## List all workspaces
```bash
bucketcloner -e <email> -t <api_token> workspace
```
This lists all workspaces, including your personal workspace, where you have access.

## Clone workspace(s)
You can clone all repositories of all workspaces by simply calling
```bash
bucketcloner -e <email> -t <api_token> clone
```
This clones all repositories of all workspaces into the folders `workspace/repository` relative to the current directory.

To select specific workspace(s), add the `-w` option with workspace slug names separated by commas
```bash
bucketcloner -e <email> -t <api_token> -w workspace1,workspace2 clone
```

All existing repositories in the folders will be deleted and cloned again. To just skip existing repositories, add `--skip-existing` flag.
```bash
bucketcloner -e <email> -t <api_token> -w workspace1,workspace2 --skip-existing clone
```

## Python example
The `example.ipynb` includes an example how to read the workspaces and download the repositories from within python.
