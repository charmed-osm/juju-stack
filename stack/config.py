# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
from typing import Dict

from stack import STACK_SEPARATOR, STACK_SEPARATOR_REPR


class Config(dict):
    """This class represents the configuration of a stack"""

    def __init__(self, config: Dict, current_model: str) -> None:
        """
        Args:
            config: Dictionary with the configuration of the stack
            default_model: Default model where the charms will be deployed to
        """
        for key, value in config.items():
            self.__setitem__(key, value)
        self.__setitem__("current-model", current_model)
        self.current_model = current_model

    def get_model(self, component_name: str) -> str:
        """
        Get model where a particular component should be deployed.

        Args:
            component_name: string of the component which model's target
                            will be returned by this function.
        """
        return (
            self.get("components", {})
            .get(component_name.replace(STACK_SEPARATOR, STACK_SEPARATOR_REPR), {})
            .get("model")
            or self.get("default-model")
            or self.current_model
        )
