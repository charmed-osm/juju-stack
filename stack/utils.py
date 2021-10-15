# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
from typing import Any, Dict, Tuple

from stack import files
from stack import status


def _is_stack_valid(stack_name: str):
    return True


def find_stacks(stack_path) -> Dict:
    stacks = {}
    stack = files.load_stack_data(stack_path)
    if _is_stack_valid(stack):
        stacks[stack["name"]] = stack
        for component_content in stack["components"].values():
            if "stack" in component_content:
                child_stack_path = "{}/{}".format(
                    stack_path, component_content["stack"]
                )
                child_stack = files.load_stack_data(child_stack_path)
                component_content["stack"] = child_stack["name"]

                child_stacks = find_stacks(child_stack_path)
                for child_stack_name, child_stack_data in child_stacks.items():
                    if child_stack_name not in stacks:
                        stacks[child_stack_name] = child_stack_data
                    elif stacks[child_stack_name] != child_stack_data:
                        raise Exception("stack already exists and it is different.")
    return stacks


def register_stacks(stacks: Dict[str, Any]):
    files.write_new_stacks_in_file(stacks)


def register_instance(
    stack_name: str, name: str, resources: Dict[str, Any], fullstack: Dict, config
):
    files.write_new_instance_in_file(stack_name, name, resources, fullstack, config)


def stack_instance_exist(name: str):
    return files.instance_exists(name)


def load_instances() -> Dict[str, Any]:
    return files.load_instances()


def get_current_model() -> str:
    return status.get_current_model()["name"]


def load_stack(stack_path: str) -> Tuple[Any, Any]:
    return files.load_stack_data(stack_path), files.load_stack_config(stack_path) or {}
