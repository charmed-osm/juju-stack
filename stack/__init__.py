# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import os
from typing import Any, Dict, List


COMPONENT_TYPES = ("stack", "charm")
STACK_SEPARATOR = "-s-"
STACK_SEPARATOR_REPR = "."
JUJU_FOLDER = "{}/.local/share/juju".format(os.getenv("HOME"))
CHARMHUB_URI = "{}/stacks.yaml".format(JUJU_FOLDER)
CHARMHUB_KEY = "stacks"
CHARMHUB_CHANNELS = ("stable", "candidate", "beta", "edge")
JUJU_INSTANCES_KEY = "instances"


class StackData(dict):
    """This class represents the data of a stack"""

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Args:
            stack_name: Name of the stack to load
        """
        for key, value in data.items():
            self.__setitem__(key, value)
        self.validate()

    @property
    def name(self) -> str:
        """Returns the description of the stack"""
        return self["name"]

    @property
    def description(self) -> str:
        """Returns the description of the stack"""
        return self.get("description", "")

    @property
    def components(self) -> Dict[str, Any]:
        """Returns a dictionary with the components name (key) and data (value)"""
        return self["components"]

    @property
    def relations(self) -> List[Any]:
        """Returns list of relations"""
        return self["relations"] if "relations" in self else []

    @property
    def provides(self) -> Dict[str, Any]:
        """Returns a dictionary with the provides endpoints"""
        return self["provides"] if "provides" in self else {}

    @property
    def requires(self) -> Dict[str, Any]:
        """Returns a dictionary with the requires endpoints"""
        return self["requires"] if "requires" in self else {}

    def validate(self) -> None:
        """Validate the current stack data"""
        # TODO: Implement validation of a stack
        pass
