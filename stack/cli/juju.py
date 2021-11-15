# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
"""
This module takes care of the juju-stack CLI commands.

For more information, execute `juju-stack --help`
"""

from functools import wraps
import logging

import click
from stack import CHARMHUB_CHANNELS, juju, StackData
from stack.charmhub import CharmHub
from stack.component import Stack
from stack.config import Config
from stack.files import (
    instance_exists,
    load_instances,
    load_stack,
    load_stack_config,
    remove_instance,
)
from stack.utils import (
    get_current_model,
)
from tabulate import tabulate
import yaml

logger = logging.getLogger()


def debug_option(f):
    @wraps(f)
    @click.option("--debug", is_flag=True, help="Print more output")
    def wrapper(debug, *args, **kwargs):
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format="%(message)s")
        return f(*args, **kwargs)

    return wrapper


@click.group()
def cli():
    juju.initialize()
    CharmHub.initialize()


@click.command(options_metavar="[options]")
@click.argument("stack_uri", metavar="<stack_uri>")
@click.argument("instance_name", metavar="<instance_name>")
@click.option(
    "--instance", "-i", metavar="<instance_file>", help="Path to the instance file"
)
@click.option(
    "--channel", metavar="<channel>", default="stable", help="The channel of the stack."
)
@debug_option
def deploy(stack_uri: str, instance_name: str, instance: str, channel: str):
    """
    Deploys a new stack instance.

    Arguments:

        stack_path: Path to the stack that will be deployed.

        instance_name: Name of the instance. It will default to the name of the stack.
    """
    logger.debug("Deploying stack")
    current_model = get_current_model()

    stack_data = None
    if stack_uri.startswith(".") or "/" in stack_uri:
        # Local stack
        if not CharmHub._valid_path(stack_uri):
            raise Exception("Not stack.yaml found in path {}.".format(stack_uri))
        data = CharmHub._load_stack_yaml(stack_uri)
        stack_data = StackData(data)
    else:
        if channel not in CHARMHUB_CHANNELS:
            raise Exception("channel `{}` is not valid".format(channel))
        if not CharmHub.is_channel_active(stack_uri, channel):
            raise Exception("no published stack in channel `{}`".format(channel))
        stack_data = CharmHub.get_stack(stack_uri, channel)
    stack_config = load_stack_config(instance) if instance else {}
    instance_name = instance_name or stack_uri
    if instance_exists(instance_name):
        logging.error(
            "A stack instance with the name {} already exists".format(instance_name)
        )
        return

    stack = Stack(stack_data)
    config = Config(
        stack_config,
        current_model=current_model,
    )
    dict(stack)

    juju.deploy_stack(stack, config, instance_name=instance_name)
    logger.info("Stack successfully deployed")


@click.command(options_metavar="[options]")
@debug_option
def list():
    """List stack instances."""
    instances = load_instances()
    stacks_info = "Stack instances:\n\n"
    for instance_name, instance_data in instances.items():
        stack_name = instance_data["stack-name"]
        resources = instance_data["resources"]
        num_charms = 0
        models = []
        for model_name, resources in resources.items():
            models.append(model_name)
            num_charms += len(resources["charms"])
        stacks_info += '\t{}: {} charms, models: "{}", stack: {}\n'.format(
            instance_name, num_charms, ", ".join(models), stack_name
        )
    logger.info(stacks_info)


@click.command(options_metavar="[options]")
@click.argument("stack_name", metavar="<stack_name>")
@debug_option
def show(stack_name):
    """Show content of a stack."""
    stack = load_stack(stack_name)
    stack = (
        yaml.dump(stack) if stack else "No stack found with name {}".format(stack_name)
    )
    logger.info("Stack information: \n\n{}".format(stack))


@click.command(options_metavar="[options]")
@click.argument("stack_instance", metavar="<stack_instance>")
@click.option("--force", is_flag=True, help="Force option")
@click.option("--no-wait", is_flag=True, help="No wait option")
@click.option("--destroy-storage", is_flag=True, help="Destroy storage option")
@debug_option
def destroy(stack_instance, force, no_wait, destroy_storage):
    """
    Destroys a stack instance.

    Arguments:

        stack_instance: Name of the stack instance to delete.
                        Execute `juju-stack list` to see the existing instances.

    """
    instances = load_instances()
    if stack_instance not in instances:
        logger.error("Stack instance {} does not exist.".format(stack_instance))
        return
    juju.destroy_stack(instances[stack_instance], force, no_wait, destroy_storage)
    remove_instance(stack_instance)
    logger.info("Removing stack {}".format(stack_instance))


@click.command(options_metavar="[options]")
@click.argument("stack_instance", metavar="<stack_instance>")
@click.option(
    "--model", "-m", metavar="<model>", help="Show the juju status of only one model"
)
@debug_option
def status(stack_instance, model):
    """
    Get the status of a stack instance.

    Arguments:

        stack_instance: Name of the stack.
                        Execute `juju-stack list` to see the existing instances.

    """
    instances = load_instances()
    if stack_instance not in instances:
        logger.error("Stack instance {} does not exist.".format(stack_instance))
        return
    components, apps, relations = juju.status(
        stack_instance, instances[stack_instance], model=model
    )
    component_headers = ["Components", "Type", "Status"]
    apps_headers = [
        "Stack",
        "Application",
        "Scale",
        "Status",
        # "Workload",
        # "Agent",
        "Model",
        "Message",
        # "Cloud/Region",
        # "Controller",
    ]
    relations_headers = ["Relation provider", "Requirer"]
    components_table = tabulate(
        [
            [
                component_name,
                components["type"],
                components["status"],
            ]
            for component_name, components in components.items()
        ],
        headers=component_headers,
        tablefmt="plain",
        numalign="left",
    )
    app_list = []
    for stack_name, apps in apps.items():
        for i, app in enumerate(apps):
            app_list.append(
                [
                    stack_name if not i else "",
                    # unit["unit"],
                    # unit["workload-status"],
                    # unit["agent-status"],
                    app["name"],
                    app["scale"],
                    app["status"],
                    app["model"],
                    app["message"],
                    # unit["cloud/region"],
                    # unit["controller"],
                ]
            )
    units_table = tabulate(
        app_list,
        headers=apps_headers,
        tablefmt="plain",
        numalign="left",
    )
    relations_table = tabulate(
        [[relation["provider"], relation["requirer"]] for relation in relations],
        headers=relations_headers,
        tablefmt="plain",
        numalign="left",
    )
    for line in components_table.splitlines():
        logger.info(line)
    logger.info("")
    for line in units_table.splitlines():
        logger.info(line)
    logger.info("")
    for line in relations_table.splitlines():
        logger.info(line)


@click.command(options_metavar="[options]")
@click.argument("stack_instance", metavar="<stack_instance>")
@debug_option
def unregister(stack_instance):
    """
    Unregister a stack instance.

    Arguments:

        stack_instance: Name of the stack.
                        Execute `juju-stack list` to see the existing instances.

    """
    instances = load_instances()
    if stack_instance not in instances:
        logger.error("Stack instance {} does not exist.".format(stack_instance))
        return
    remove_instance(stack_instance)
    logger.info("Stack {} unregistered".format(stack_instance))


def main():
    try:
        commands = [deploy, list, show, destroy, status, unregister]
        for c in commands:
            cli.add_command(c)
        cli()
        exit(0)
    except Exception as e:
        logger.error(e)
    exit(1)


if __name__ == "__main__":
    main()
