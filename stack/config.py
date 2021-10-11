# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
from typing import Dict, NoReturn

from stack import STACK_SEPARATOR, STACK_SEPARATOR_REPR


class Config:
    """This class represents the configuration of a stack"""

    def __init__(self, config: Dict, default_model: str) -> NoReturn:
        """
        Args:
            config: Dictionary with the configuration of the stack
            default_model: Default model where the charms will be deployed to
        """
        self._config = config
        self.default_model = default_model

    def get_model(self, component_name: str) -> str:
        """
        Get model where a particular component should be deployed.

        Args:
            component_name: string of the component which model's target
                            will be returned by this function.
        """
        return (
            self._config.get("components", {})
            .get(component_name.replace(STACK_SEPARATOR, STACK_SEPARATOR_REPR), {})
            .get("model")
            or self.default_model
        )
