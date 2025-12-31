from typing import Any, Dict, List, Optional

import pytest

from bucketcloner.main import (
    AuthMode,
    _get_repository_clone_url,
    _get_workspaces,
    add_credentials,
)


class TestAddCredentials:
    """Test cases for add_credentials function."""

    @pytest.mark.parametrize(
        ("url", "token", "expected_url"),
        [
            (
                "https://bitbucket.org/user/repo.git",
                "test_token",
                "https://x-bitbucket-api-token-auth:test_token@bitbucket.org/user/repo.git",
            ),
            (
                "https://old_user:old_pass@bitbucket.org/user/repo2.git",
                "new_token",
                "https://x-bitbucket-api-token-auth:new_token@bitbucket.org/user/repo2.git",
            ),
            (
                "https://bitbucket.org/workspace/project/repo.git",
                "test_token",
                "https://x-bitbucket-api-token-auth:test_token@bitbucket.org/workspace/project/repo.git",
            ),
        ],
    )
    def test_add_credentials_valid_urls(
        self, url: str, token: str, expected_url: str
    ) -> None:
        """Test adding credentials to valid URLs."""
        result: Optional[str] = add_credentials(url, token)

        assert result is not None
        assert expected_url == result
        assert result.startswith("https://")

    def test_add_credentials_with_special_characters_in_token(self) -> None:
        """Test that special characters in token are URL-encoded."""
        url: str = "https://bitbucket.org/user/repo.git"
        token: str = "token@with!special#chars"  # noqa: S105
        result: Optional[str] = add_credentials(url, token)

        assert result is not None
        assert "token%40with%21special%23chars" in result

    @pytest.mark.parametrize(
        "url",
        [
            "invalid_url",
            "no_separator_here",
            "justtext",
        ],
    )
    def test_add_credentials_invalid_urls(self, url: str) -> None:
        """Test with invalid URLs that have no @ or //."""
        result: Optional[str] = add_credentials(url, "test_token")

        assert result is None


class TestGetRepositoryCloneUrl:
    """Test cases for _get_repository_clone_url function."""

    @pytest.mark.parametrize(
        ("auth_mode", "input_url", "should_have_credentials"),
        [
            (AuthMode.HTTPS, "https://bitbucket.org/user/repo.git", True),
            (AuthMode.SSH, "git@bitbucket.org:user/repo.git", False),
        ],
    )
    def test_get_clone_url_different_auth_modes(
        self, auth_mode: AuthMode, input_url: str, should_have_credentials: bool
    ) -> None:
        """Test retrieving clone URLs with different authentication modes."""
        repo: Dict[str, Any] = {
            "name": "test-repo",
            "links": {
                "clone": [
                    {"name": auth_mode.value.lower(), "href": input_url},
                ]
            },
        }
        result: Optional[str] = _get_repository_clone_url(repo, auth_mode, "test_token")

        assert result is not None
        if should_have_credentials:
            assert "x-bitbucket-api-token-auth:test_token" in result
        else:
            assert "x-bitbucket-api-token-auth:test_token" not in result

    @pytest.mark.parametrize(
        ("clone_links", "auth_mode"),
        [
            ([], AuthMode.HTTPS),
            (
                [{"name": "ssh", "href": "git@bitbucket.org:user/repo.git"}],
                AuthMode.HTTPS,
            ),
            (
                [{"name": "https", "href": "https://bitbucket.org/user/repo.git"}],
                AuthMode.SSH,
            ),
        ],
    )
    def test_get_clone_url_missing_or_unavailable(
        self, clone_links: List[Dict[str, str]], auth_mode: AuthMode
    ) -> None:
        """Test when requested clone type is not available."""
        repo: Dict[str, Any] = {
            "name": "test-repo",
            "links": {"clone": clone_links},
        }
        result: Optional[str] = _get_repository_clone_url(repo, auth_mode, "test_token")

        assert result is None


class TestGetWorkspaces:
    """Test cases for _get_workspaces function (only when workspaces != None)."""

    @pytest.mark.parametrize(
        ("workspaces_input", "expected_output"),
        [
            ("workspace1", ["workspace1"]),
            (
                "workspace1,workspace2,workspace3",
                ["workspace1", "workspace2", "workspace3"],
            ),
        ],
    )
    def test_get_workspaces_valid_inputs(
        self, workspaces_input: str, expected_output: List[str]
    ) -> None:
        """Test parsing various valid workspace inputs."""
        result: List[str] = _get_workspaces("email@test.com", "token", workspaces_input)

        assert isinstance(result, list)
        assert result == expected_output
