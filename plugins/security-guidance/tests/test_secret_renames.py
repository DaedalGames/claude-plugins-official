"""A tracked file renamed away from a secret-shaped name stays out of the
Stop review, however the rename reached git."""
import os

import pytest

from conftest import (
    GIT_ENV, bash_payload, commit_file, git, make_repo, metrics_of, run_hook,
    stop_payload, ups_payload,
)

import diffstate
import gitutil

SECRET_BODY = "".join(f"KEY_{i}=SECRET_VALUE_{i}\n" for i in range(30))
EDIT = "import os\nos.system(input())\n"


def _repo(tmp_path):
    return make_repo(tmp_path / "repo", {"deploy_rsa": SECRET_BODY, "app.py": "x = 1\n"})


def _sent(stub_api):
    return "".join(stub_api.bodies)


def _rename(repo, how):
    if how == "moved":
        os.rename(repo / "deploy_rsa", repo / "settings.py")
        return
    git(repo, "mv", "deploy_rsa", "settings.py")
    if how == "committed":
        git(repo, "commit", "-qm", "rename")
    elif how == "amended":
        git(repo, "commit", "-q", "--amend", "-m", "init, renamed")
        # Edited after the commit, so the file is still part of the turn.
        with open(repo / "settings.py", "a") as f:
            f.write("KEY_NEW=SECRET_VALUE_NEW\n")


@pytest.mark.parametrize("how", ["moved", "staged", "committed", "amended"])
def test_stop_review_leaves_the_renamed_file_out(tmp_path, hook_env, stub_api, how):
    repo = _repo(tmp_path)
    run_hook(ups_payload(repo), hook_env)
    _rename(repo, how)
    (repo / "app.py").write_text(EDIT)
    _rc, stdout, _err = run_hook(stop_payload(repo), hook_env)
    m = metrics_of(stdout)
    assert m.get("skip_reason") is None, m
    assert m.get("files_reviewed") == 1
    assert "os.system" in _sent(stub_api)
    assert "SECRET_VALUE" not in _sent(stub_api)


def test_stop_review_with_nothing_but_the_rename_sends_nothing(tmp_path, hook_env, stub_api):
    repo = _repo(tmp_path)
    run_hook(ups_payload(repo), hook_env)
    git(repo, "mv", "deploy_rsa", "settings.py")
    _rc, stdout, _err = run_hook(stop_payload(repo), hook_env)
    assert metrics_of(stdout).get("skip_reason") == 7
    assert stub_api.bodies == []


def test_commit_review_leaves_the_renamed_file_out(tmp_path, hook_env, stub_api):
    repo = _repo(tmp_path)
    git(repo, "mv", "deploy_rsa", "settings.py")
    _sha, out = commit_file(repo, "app.py", EDIT)
    run_hook(bash_payload(repo, "git commit -m change", stdout=out), hook_env)
    assert "os.system" in _sent(stub_api)
    assert "SECRET_VALUE" not in _sent(stub_api)


@pytest.fixture
def git_env(monkeypatch):
    """The suite's git settings for calls made in this process."""
    for k, v in GIT_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(gitutil, "_secret_rename_origins", {})
    monkeypatch.setattr(diffstate, "_secret_rename_origins", gitutil._secret_rename_origins)


def test_listings_are_unchanged_and_note_the_secret_origin(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", {
        "deploy_rsa": SECRET_BODY, "old name.py": SECRET_BODY + "x = 1\n",
        "gone.py": "x = 1\n", "edit.py": "x = 1\n"})
    git(repo, "mv", "deploy_rsa", "settings.py")
    git(repo, "mv", "old name.py", "new name.py")
    git(repo, "rm", "-q", "gone.py")
    (repo / "edit.py").write_text("x = 2\n")
    names = {"settings.py", "new name.py", "gone.py", "edit.py"}
    assert gitutil._git_name_only(str(repo), "HEAD") == names
    assert gitutil._secret_rename_origins == {"settings.py": "deploy_rsa"}
    gitutil._secret_rename_origins.clear()
    assert gitutil._git_status_porcelain(str(repo)) == (names, set())
    assert gitutil._secret_rename_origins == {"settings.py": "deploy_rsa"}


def test_review_set_gains_only_the_origin_of_a_reviewed_file(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", {
        "deploy_rsa": SECRET_BODY, "old.py": SECRET_BODY + "x = 1\n"})
    git(repo, "mv", "deploy_rsa", "settings.py")
    git(repo, "mv", "old.py", "new.py")
    paths, _base, root, _untracked, metrics = diffstate.compute_v2_review_set(str(repo), None, None, {})
    assert sorted(os.path.relpath(p, root) for p in paths) == ["deploy_rsa", "new.py", "settings.py"]
    assert metrics["dirty_now_count"] == 2 and metrics["review_set_count"] == 3
