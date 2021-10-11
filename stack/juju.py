# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
import subprocess
import time
from typing import Any, Dict, NoReturn

from stack import STACK_SEPARATOR, STACK_SEPARATOR_REPR
from stack.component import ResourceType, Stack
from stack.config import Config
from stack.files import load_stack
import yaml


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
        return plan.info()


def destroy_stack(
    instance: Dict[str, Any], force, no_wait, destroy_storage
) -> NoReturn:
    """
    Destroy a stack

    Args:
        instance: Data with the resources to delete
    """
    # TODO: Rethink how the destroy will be done
    force = True
    no_wait = True

    removed_instance = {}
    for model_name, model_resources in instance.get("resources").items():
        removed_instance[model_name] = {
            ResourceType.CHARM.value: [],
            ResourceType.SAAS.value: [],
            ResourceType.OFFER.value: [],
        }
        for saas in model_resources[ResourceType.SAAS.value]:
            command = ["juju", "remove-saas", saas, "-m", model_name]
            subprocess.run(command, check=True)
            removed_instance[model_name][ResourceType.SAAS.value].append(saas)
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


def status(instance_name: str, instance: Dict[str, Any], model: str = None) -> str:
    """
    Get the status of a stack instance

    Args:
        instance_name: Stack instance name
        instance: Data with the resources of the stack
        model: Model name
    """
    if model:
        return (
            subprocess.run(
                ["juju", "status", "--color", "-m", model, "{}*".format(instance_name)],
                capture_output=True,
                check=True,
            )
            .stdout.decode("utf-8")
            .replace(STACK_SEPARATOR, STACK_SEPARATOR_REPR)
        )
    stack = load_stack(instance["stack-name"])
    num_charms = 0
    active_charms = 0
    models = []
    cmr = []
    stack_status = "active"
    for model_name, resources in instance["resources"].items():
        juju_status = yaml.safe_load(
            subprocess.run(
                [
                    "juju",
                    "status",
                    "-m",
                    model_name,
                    "--format=yaml",
                    "{}*".format(instance_name),
                ],
                capture_output=True,
                check=True,
            ).stdout.decode("utf-8")
        )
        for saas_name, saas_data in juju_status.get(
            "application-endpoints", {}
        ).items():
            offer_uri = saas_data["url"].split("/")[1]
            for offer_endpoint, relations in saas_data["relations"].items():
                for consume_application in relations:
                    cmr.append(
                        "{}:{} <-----> {}.{}".format(
                            offer_uri, offer_endpoint, model_name, consume_application
                        )
                    )
        applications = []
        for application_name, application_data in juju_status["applications"].items():
            num_charms += 1
            units = []
            active = True
            for unit_name, unit_data in application_data["units"].items():
                unit_status = unit_data["workload-status"]["current"]
                if unit_status != "active":
                    stack_status = unit_status
                    active = False
                units.append(
                    {
                        unit_name: [
                            {
                                "Status": "{}, {}".format(
                                    unit_status, unit_data["juju-status"]["current"]
                                )
                            },
                            {
                                "Address (Ports)": "{} ({})".format(
                                    unit_data.get("address"),
                                    " ".join(unit_data.get("open-ports", [])),
                                )
                            },
                            {
                                "Message": unit_data["workload-status"].get(
                                    "message", ""
                                )
                            },
                        ]
                    }
                )
            if active:
                active_charms += 1
            applications.append(
                {
                    application_name: [
                        {"Version": application_data.get("version")},
                        {"Status": application_data["application-status"]["current"]},
                        {"Address": application_data.get("address")},
                        {"Units": units},
                    ]
                }
            )
        models.append(
            {
                model_name: [
                    {
                        "Controller": "{} ({})".format(
                            juju_status["model"]["controller"],
                            juju_status["model"]["type"],
                        )
                    },
                    {
                        "Cloud/Region": "{}/{}".format(
                            juju_status["model"]["cloud"],
                            juju_status["model"]["region"],
                        )
                    },
                    {"Version": juju_status["model"]["version"]},
                    {"Applications": applications},
                ]
            }
        )
    output = [
        {
            "Summary": [
                {"Name": stack["name"]},
                {"Status": stack_status},
                {"Description": stack.get("description")},
                {"Models": ", ".join(instance["resources"].keys())},
                {"Applications": num_charms},
                {"Active applications": "{}/{}".format(active_charms, num_charms)},
            ]
        },
        {"Models": models},
        {"Cross-model relations": cmr},
    ]
    return yaml.dump(output).replace("- ", "").replace("-s-", ".")
