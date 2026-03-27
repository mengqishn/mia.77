#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Tuple


DEFAULT_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_CHROME_USER_DATA_DIR = str(Path.home() / "Library/Application Support/Google/Chrome")
DEFAULT_PROFILE_DIRECTORY = "Default"


def add_browser_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--headless", action="store_true", help="run Chrome in headless mode")
    parser.add_argument(
        "--chrome-path",
        default=DEFAULT_CHROME_PATH,
        help="path to the Chrome executable",
    )
    parser.add_argument(
        "--user-data-dir",
        default=DEFAULT_CHROME_USER_DATA_DIR,
        help="Chrome user data dir, usually ~/Library/Application Support/Google/Chrome",
    )
    parser.add_argument(
        "--profile-directory",
        default=DEFAULT_PROFILE_DIRECTORY,
        help="Chrome profile directory name, usually Default or Profile 1",
    )
    parser.add_argument(
        "--no-copy-profile",
        action="store_true",
        help="launch directly against the live Chrome profile instead of cloning it to a temp dir",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=0,
        help="slow down Playwright actions by N milliseconds",
    )
    parser.add_argument(
        "--cdp-url",
        help="connect to an already running Chrome via CDP, for example http://127.0.0.1:9222",
    )


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "playwright is not installed. Run `python3 -m pip install --user playwright` first."
        ) from exc
    return sync_playwright


def validate_browser_paths(chrome_path: str, user_data_dir: str, profile_directory: str) -> None:
    chrome = Path(chrome_path).expanduser()
    user_dir = Path(user_data_dir).expanduser()
    profile_dir = user_dir / profile_directory

    if not chrome.exists():
        raise FileNotFoundError(f"Chrome executable not found: {chrome}")
    if not user_dir.exists():
        raise FileNotFoundError(f"Chrome user data dir not found: {user_dir}")
    if not profile_dir.exists():
        raise FileNotFoundError(f"Chrome profile dir not found: {profile_dir}")


def ensure_cdp_url(cdp_url: str) -> None:
    if not cdp_url:
        raise ValueError("cdp_url is required")
    if not cdp_url.startswith("http://") and not cdp_url.startswith("ws://"):
        raise ValueError(f"Unsupported cdp_url: {cdp_url}")


def can_connect_to_cdp_http(cdp_url: str) -> bool:
    if not cdp_url.startswith("http://"):
        return True
    try:
        from urllib.parse import urlparse

        parsed = urlparse(cdp_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9222
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def clone_chrome_profile(user_data_dir: str, profile_directory: str) -> Tuple[Path, Path]:
    source_root = Path(user_data_dir).expanduser()
    temp_root = Path(tempfile.mkdtemp(prefix="redbook-chrome-profile-"))
    _copy_if_exists(source_root / "Local State", temp_root / "Local State")
    _copy_if_exists(source_root / profile_directory, temp_root / profile_directory)
    return temp_root, temp_root / profile_directory


@contextmanager
def chrome_profile_dir(
    user_data_dir: str,
    profile_directory: str,
    no_copy_profile: bool,
) -> Iterator[Tuple[str, str]]:
    if no_copy_profile:
        yield str(Path(user_data_dir).expanduser()), profile_directory
        return

    temp_root, _ = clone_chrome_profile(user_data_dir, profile_directory)
    try:
        yield str(temp_root), profile_directory
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


@contextmanager
def launch_persistent_context(
    chrome_path: str,
    user_data_dir: str,
    profile_directory: str,
    headless: bool,
    no_copy_profile: bool,
    slow_mo: int = 0,
):
    validate_browser_paths(chrome_path, user_data_dir, profile_directory)
    sync_playwright = ensure_playwright()

    with chrome_profile_dir(user_data_dir, profile_directory, no_copy_profile) as (
        runtime_user_data_dir,
        runtime_profile_directory,
    ):
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch_persistent_context(
            runtime_user_data_dir,
            executable_path=str(Path(chrome_path).expanduser()),
            headless=headless,
            slow_mo=slow_mo,
            args=[
                f"--profile-directory={runtime_profile_directory}",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1440, "height": 1200},
        )
        try:
            yield browser
        finally:
            browser.close()
            playwright.stop()


@contextmanager
def connect_over_cdp(
    cdp_url: str,
    slow_mo: int = 0,
):
    ensure_cdp_url(cdp_url)
    if not can_connect_to_cdp_http(cdp_url):
        raise RuntimeError(
            f"Cannot connect to CDP at {cdp_url}. Start Chrome with remote debugging first."
        )
    sync_playwright = ensure_playwright()
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp(cdp_url, slow_mo=slow_mo)
    created_context = None
    try:
        if browser.contexts:
            yield browser.contexts[0]
        else:
            created_context = browser.new_context(viewport={"width": 1440, "height": 1200})
            yield created_context
    finally:
        if created_context is not None:
            created_context.close()
        # Do not call browser.close() here, to avoid closing the user's live Chrome.
        playwright.stop()


@contextmanager
def launch_browser_context(
    chrome_path: str,
    user_data_dir: str,
    profile_directory: str,
    headless: bool,
    no_copy_profile: bool,
    slow_mo: int = 0,
    cdp_url: str | None = None,
):
    if cdp_url:
        with connect_over_cdp(cdp_url=cdp_url, slow_mo=slow_mo) as context:
            yield context
        return

    with launch_persistent_context(
        chrome_path=chrome_path,
        user_data_dir=user_data_dir,
        profile_directory=profile_directory,
        headless=headless,
        no_copy_profile=no_copy_profile,
        slow_mo=slow_mo,
    ) as context:
        yield context


def dumps_pretty(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
