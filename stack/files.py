""" Module in charge of handling stack files """
import os
from typing import Any, Dict

import yaml


def load_stack(stack_name: str):
    stacks = load_stacks_file()
    return stacks["stacks"].get(stack_name)


def load_stack_data(
    stack_name: str,
) -> dict:
    """Load the Stack Metadata file of a specific Stack"""
    filename = "{}/stack.yaml".format(stack_name)
    if not os.path.isfile(filename):
        return None

    with open(filename) as file_stream:
        return yaml.safe_load(file_stream)


def load_stack_config(
    stack_path: str,
) -> dict:
    """Load the Stack Config file of a specific Stack"""
    filename = "{}/config.yaml".format(stack_path)
    if not os.path.isfile(filename):
        return None

    with open(filename) as file_stream:
        return yaml.safe_load(file_stream)


def load_stacks_file() -> dict:
    """Load complete Local Stacks File"""
    home = os.getenv("HOME")
    filename = "{}/.local/share/juju/stacks.yaml".format(home)

    if not os.path.isfile(filename):
        open(filename, "w").close()

    with open(filename, "r") as s_file:
        stacks = yaml.safe_load(s_file)

    if stacks is None:
        return {"stacks": {}, "instances": {}}

    return stacks


def write_stacks_file(content: dict) -> dict:
    """Overwrite Local Stacks File"""
    home = os.getenv("HOME")

    with open("{}/.local/share/juju/stacks.yaml".format(home), "w") as s_file:
        s_file.write(yaml.dump(content))


def write_new_stacks_in_file(new_stacks: dict):
    """Write a new Stack in the local Stacks file"""
    stacks = load_stacks_file()
    if stacks is None:
        stacks = {}
    if "stacks" not in stacks:
        stacks["stacks"] = {}

    stacks["stacks"].update(new_stacks)

    write_stacks_file(stacks)


def write_new_instance_in_file(stack_name: str, name: str, resources: Dict[str, Any]):
    """Write a new Stack in the local Stacks file"""
    stacks = load_stacks_file()
    if stacks is None:
        stacks = {}
    if "instances" not in stacks:
        stacks["instances"] = {}

    stacks["instances"][name] = {"stack-name": stack_name, "resources": resources}

    write_stacks_file(stacks)


def instance_exists(name: str):
    stacks = load_stacks_file()
    return name in stacks.get("instances")


def load_instances():
    stacks = load_stacks_file()
    return stacks.get("instances", [])


def remove_instance(instance_name):
    stacks = load_stacks_file()
    stacks["instances"].pop(instance_name)
    write_stacks_file(stacks)


def update_stack_in_file(model: str, stack_name: str, stack: dict):
    """Updates an existing stack in stackfile"""
    stacks = load_stacks_file()

    stacks[model][stack_name] = stack

    write_stacks_file(stacks)


def delete_stack_in_file(model: str, stack_name: str):
    """Delete a Stack from the local Stack file"""
    stacks = load_stacks_file()

    del stacks[model][stack_name]

    write_stacks_file(stacks)
