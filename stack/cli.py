# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
"""
This module takes care of the juju-stack CLI commands.

For more information, execute `juju-stack --help`
"""

from functools import wraps
import logging

import click
from stack import juju
from stack.component import Stack
from stack.config import Config
from stack.files import (
    instance_exists,
    load_instances,
    load_stack,
    load_stack_config,
    load_stack_data,
    remove_instance,
)
from stack.utils import (
    find_stacks,
    get_current_model,
    register_instance,
    register_stacks,
)
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
    pass


@click.command(options_metavar="[options]")
@click.argument("stack_path", metavar="<stack_path>")
@click.argument("instance_name", metavar="[<instance_name>]")
@click.option(
    "--config", "-c", metavar="<path_to_config>", help="Path to the config.yaml"
)
@debug_option
def deploy(stack_path: str, instance_name: str, config: str):
    """
    Deploys a new stack instance.

    Arguments:

        stack_path: Path to the stack that will be deployed.

        instance_name: Name of the instance. It will default to the name of the stack.
    """
    logger.debug("Deploying stack")
    current_model = get_current_model()
    stack_data = load_stack_data(stack_path)
    stack_config = load_stack_config(config) if config else {}
    instance_name = instance_name or stack_data["name"]
    if instance_exists(instance_name):
        logging.error(
            "A stack instance with the name {} already exists".format(instance_name)
        )
        return
    # Store the stacks
    stacks = find_stacks(stack_path)
    register_stacks(stacks)
    # Load stack, its config, and deploy
    stack = Stack(stack_data["name"])
    config = Config(
        stack_config,
        default_model=current_model,
    )
    info = juju.deploy_stack(stack, config, instance_name=instance_name)
    logger.debug("Deployed resources: {}".format(info))
    register_instance(stack_data["name"], instance_name, info)
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
@debug_option
def status(stack_instance):
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
    status = juju.status(stack_instance, instances[stack_instance])
    logger.info(status)


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
        import traceback

        print("failed: {} {}".format(e, traceback.format_exc()))
    exit(1)


if __name__ == "__main__":
    main()
