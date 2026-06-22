"""Platform-aware Jira subtask filtering."""

from __future__ import annotations


PLATFORM_SUBTASK_MARKERS = {
    "api": (
        "[be]",
        " backend ",
        " api ",
        " endpoint",
        " contract",
        " payload",
        " schema",
    ),
    "android": (
        "[mobile]",
        " mobile ",
        " android ",
        " appium ",
        " flutter ",
    ),
    "ios": (
        "[mobile]",
        " mobile ",
        " ios ",
        " appium ",
        " flutter ",
    ),
    "flutter-android": (
        "[mobile]",
        " mobile ",
        " android ",
        " appium ",
        " flutter ",
    ),
    "flutter-ios": (
        "[mobile]",
        " mobile ",
        " ios ",
        " appium ",
        " flutter ",
    ),
    "database": (
        "[db]",
        " database ",
        " db ",
        " sql ",
        " query ",
        " migration ",
    ),
    "web": (
        "[fe]",
        " frontend ",
        " front-end ",
        " web ",
        " cms ",
        " browser ",
        " playwright ",
    ),
}


def subtask_matches_platform(subtask: dict, platforms: list[str]) -> bool:
    text = f" {subtask.get('summary', '')} {subtask.get('description', '')} ".lower()
    markers = []
    for platform in platforms:
        markers.extend(PLATFORM_SUBTASK_MARKERS.get(platform, ()))
    return any(marker in text for marker in markers)


def filter_subtasks_for_platforms(subtasks: list[dict], platforms: list[str]) -> list[dict]:
    if not subtasks:
        return []
    filtered = [
        subtask for subtask in subtasks
        if subtask_matches_platform(subtask, platforms)
    ]
    return filtered or subtasks
