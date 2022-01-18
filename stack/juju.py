# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import subprocess
import time
from typing import Any, Dict, Tuple


from stack import (
    CHARMHUB_KEY,
    CHARMHUB_URI,
    JUJU_FOLDER,
    JUJU_INSTANCES_KEY,
    STACK_SEPARATOR,
)
from stack.component import ResourceType, Stack
from stack.config import Config
from stack.utils import register_instance
import yaml


def initialize() -> None:
    subprocess.run(["mkdir", "-p", JUJU_FOLDER], check=True)
    subprocess.run(["touch", CHARMHUB_URI], check=True)
    stacks = None
    with open(CHARMHUB_URI, "r") as f:
        stacks = yaml.safe_load(f)
    with open(CHARMHUB_URI, "w") as f:
        if stacks is None:
            stacks = {}
        if isinstance(stacks, Dict) and CHARMHUB_KEY not in stacks:
            stacks[CHARMHUB_KEY] = {}
        if isinstance(stacks, Dict) and JUJU_INSTANCES_KEY not in stacks:
            stacks[JUJU_INSTANCES_KEY] = {}
        f.write(yaml.dump(stacks))


def deploy_stack(
    stack: Stack, config: Config, instance_name: str = None
) -> Dict[str, Any]:
    """
    Deploy a stack with configuration

    Args:
        stack: Stack object to be deployed
        config: Configuration object
        instance_name: Name of the instance.
                        If not specified, the name of the stack will be used.
    Returns:
        A dictionary containing the resources
    """
    if not instance_name:
        instance_name = stack.stack_name

    plan = stack.get_plan(instance_name, config)
    try:
        plan.deploy()
    except Exception as e:
        print("deployent failed {}".format(e))
    finally:
        register_instance(
            stack.data.name, instance_name, plan.info(), dict(stack), dict(config)
        )


def destroy_stack(instance: Dict[str, Any], force, no_wait, destroy_storage) -> None:
    """
    Destroy a stack

    Args:
        instance: Data with the resources to delete
    """
    # TODO: Rethink how the destroy will be done
    force = True
    no_wait = True

    removed_instance = {}
    saas_removed = False
    for model_name, model_resources in instance.get("resources").items():
        removed_instance[model_name] = {
            ResourceType.CHARM.value: [],
            ResourceType.SAAS.value: [],
            ResourceType.OFFER.value: [],
        }
        for saas in model_resources[ResourceType.SAAS.value]:
            command = ["juju", "remove-saas", saas, "-m", model_name]
            subprocess.run(command, check=True)
            saas_removed = True
            removed_instance[model_name][ResourceType.SAAS.value].append(saas)
    if saas_removed:
        time.sleep(5)
    for model_name, model_resources in instance.get("resources").items():
        for offer in model_resources[ResourceType.OFFER.value]:
            command = ["juju", "remove-offer", offer, "-y"]
            if force:
                command.append("--force")
            subprocess.run(command, check=True)
            removed_instance[model_name][ResourceType.OFFER.value].append(offer)

    for model_name, model_resources in instance.get("resources").items():
        for charm in model_resources[ResourceType.CHARM.value]:
            command = ["juju", "remove-application", charm, "-m", model_name]
            if force:
                command.append("--force")
            if no_wait:
                command.append("--no-wait")
            if destroy_storage:
                command.append("--destroy-storage")
            subprocess.run(command, check=True)
            removed_instance[model_name][ResourceType.CHARM.value].append(charm)


def _get_status_with_color(status: str) -> str:
    green_status = ("active", "idle", "executing")
    red_status = ("error", "blocked", "terminated")
    yellow_status = ("allocating", "maintenance")
    colored_status = None
    if status in green_status:
        colored_status = "\033[32m{}\033[0m".format(status)
    elif status in red_status:
        colored_status = "\033[31m{}\033[0m".format(status)
    elif status in yellow_status:
        colored_status = "\033[33m{}\033[0m".format(status)
    else:
        colored_status = status
    return colored_status


def _get_model(instance_name, instance_data):
    instance_name_list = instance_name.split(".")
    instance_name_list.pop(0)
    component_name_in_config = ".".join(instance_name_list)
    return (
        instance_data["config"]
        .get("components", {})
        .get(component_name_in_config, {})
        .get("model")
        or instance_data["config"].get("default-model")
        or instance_data["config"].get("current-model")
    )


def _get_relation_data(endpoint_component, endpoint_interface, stack_data):
    endpoint = None
    interface = None
    component_data = stack_data["components"][endpoint_component]
    component_type = "charm" if "charm" in component_data else "stack"
    if component_type == "charm":
        endpoint = endpoint_component
        interface = endpoint_interface
    else:
        if endpoint_interface in component_data.get("provides", {}):
            e_component, endpoint_interface = component_data["provides"][
                endpoint_interface
            ]["forward"].split(":")
        else:
            e_component, endpoint_interface = component_data["requires"][
                endpoint_interface
            ]["forward"].split(":")
        stack_endpoint, stack_interface = _get_relation_data(
            e_component, endpoint_interface, component_data
        )
        endpoint = "{}.{}".format(endpoint_component, stack_endpoint)
        interface = stack_interface
    return endpoint, interface


_juju_status = {}


def _get_apps_and_relations(instance_name, instance, stack):
    apps = {}
    relations = []
    charm_components = {k: v for k, v in stack["components"].items() if "charm" in v}
    stack_components = {
        k: v for k, v in stack["components"].items() if "charm" not in v
    }

    for relation in stack.get("relations", []):
        splitted_provider = relation["provider"].split(":")
        splitted_requirer = relation["requirer"].split(":")
        provider_component = splitted_provider.pop(0)
        requirer_component = splitted_requirer.pop(0)
        interface = "unknown"
        if splitted_requirer:
            interface = splitted_requirer[0]
        elif splitted_provider:
            interface = splitted_provider[0]
        provider_endpoint, _ = _get_relation_data(provider_component, interface, stack)
        requirer_endpoint, _ = _get_relation_data(requirer_component, interface, stack)
        relations.append(
            {
                "provider": "{}.{}".format(instance_name, provider_endpoint),
                "requirer": "{}.{}".format(instance_name, requirer_endpoint),
                "interface": "-",
            }
        )
    if charm_components:
        apps[instance_name] = []
        for charm_name in charm_components.keys():
            model = _get_model(instance_name, instance)
            if model not in _juju_status:
                _juju_status[model] = yaml.safe_load(
                    subprocess.run(
                        [
                            "juju",
                            "status",
                            "-m",
                            model,
                            "--format=yaml",
                        ],
                        capture_output=True,
                        check=True,
                    ).stdout.decode("utf-8")
                )
            for application_full_name, application_data in _juju_status[model][
                "applications"
            ].items():
                application_name_components = application_full_name.split(
                    STACK_SEPARATOR
                )
                application_name = application_name_components.pop()
                if (
                    application_name == charm_name
                    and ".".join(application_name_components) == instance_name
                ):
                    apps[instance_name].append(
                        {
                            "name": application_name,
                            "scale": application_data["scale"],
                            "status": application_data["application-status"]["current"],
                            "message": application_data["application-status"].get(
                                "message", ""
                            ),
                            "model": model,
                        }
                    )
    if stack_components:
        for stack_name, stack in stack_components.items():
            new_instance_name = "{}.{}".format(instance_name, stack_name)
            child_units, child_relations = _get_apps_and_relations(
                new_instance_name, instance, stack
            )
            relations.extend(child_relations)
            for s_name, data in child_units.items():
                apps[s_name] = data
    return apps, relations


def _update_components_status(instance_name, components, apps):
    for component_name, component in components.items():
        full_name = (
            "{}.{}".format(instance_name, component_name)
            if component["type"] == "stack"
            else instance_name
        )
        statuses = []
        for stack_name, unit_list in apps.items():
            condition = False
            if full_name == instance_name:
                condition = full_name == stack_name
            else:
                if stack_name.count(".") > 1:
                    condition = "{}.".format(full_name) in stack_name
                else:
                    condition = "{}".format(full_name) == stack_name
            if condition:
                for units_data in unit_list:
                    statuses.append(units_data["status"])
        if "error" in statuses:
            component["status"] = "error"
        elif "blocked" in statuses:
            component["status"] = "blocked"
        elif "maintenance" in statuses:
            component["status"] = "maintenance"
        elif "waiting" in statuses:
            component["status"] = "waiting"
        elif "active" in statuses:
            component["status"] = "active"
        else:
            component["status"] = "unknown"

        component["status"] = _get_status_with_color(component["status"])
    for app_list in apps.values():
        for app in app_list:
            app["status"] = _get_status_with_color(app["status"])
            # unit["workload-status"] = _get_status_with_color(unit["workload-status"])


def status(instance_name: str, instance: Dict[str, Any]) -> Tuple:
    """
    Get the status of a stack instance

    Args:
        instance_name: Stack instance name
        instance: Data with the resources of the stack
        model: Model name
    """
    components = {
        component_name: {
            "type": "stack" if "components" in component else "charm",
            "status": "Unknown",
        }
        for component_name, component in instance["fullstack"]["components"].items()
    }
    relations = []
    apps, relations = _get_apps_and_relations(
        instance_name, instance, instance["fullstack"]
    )
    _update_components_status(instance_name, components, apps)
    return (components, apps, relations)
