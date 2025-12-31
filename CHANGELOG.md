# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0]

## Changed
- Switched to API token authentication, as user/password is deprecated (thanks @gkffzs)
- Moved to uv as build backend with dev dependencies
- Switched tests to pytest

## Added
- Pull existing repositories instead of deleting and cloning with `--refresh`/`-r` flag
- Define the base folder for the clone with `--base-folder`
- Create project folders under the workspace folder with `--project-folder` flag
- Auth mode to select between `https` cloning using the API token and `ssh` using an ssh key
- Pre-commit hooks
- Changelog

## [0.2.0]

### Added
- Limit the clone to a specific project (thanks @borisssmidtCET)

## [0.1.0]
Initial version
