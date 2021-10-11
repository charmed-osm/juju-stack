# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
"""
Module in charge of representing the status
"""
import re
import subprocess

import yaml


def get_current_model() -> dict:
    """Get the currently used model which its information"""
    status = get_juju_status()
    return status["model"]


def get_juju_status() -> dict:
    """Get juju status converted into a dictionary"""
    cmd = ["juju", "status", "--format", "yaml"]
    result = subprocess.run(cmd, capture_output=True, check=True)
    return yaml.safe_load(result.stdout)


def show_juju_status(cmd: list):
    """Print Juju status with . namespace naming"""
    cmd = ["juju"] + cmd + ["--color"]

    result = subprocess.run(cmd, capture_output=True, check=True)

    result = result.stdout.decode("utf-8")
    substituted_words = re.findall("[^\s]+-s-[^\s]+\s", result)

    for s_word in substituted_words:
        result = result.replace(s_word, s_word.replace("-s-", ".") + "  ")

    print(result)
