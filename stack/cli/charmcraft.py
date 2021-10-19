# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
"""
This module takes care of the charmcraft-stack CLI commands.

For more information, execute `charmcraft-stack --help`
"""

from functools import wraps
import logging

import click
from stack.charmhub import CharmHub
from tabulate import tabulate

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
    CharmHub.initialize()


@click.command(options_metavar="[options]")
@click.argument("name", metavar="<name>")
@debug_option
def register(name):
    CharmHub.register(name)
    logger.info("stack {} has been successfully registered".format(name))


@click.command(options_metavar="[options]")
@click.argument("name", metavar="<name>")
@debug_option
def unregister(name):
    CharmHub.unregister(name)


@click.command(options_metavar="[options]")
@debug_option
def names():
    headers = ["Name", "Type", "Visibility", "Status"]
    stacks = CharmHub.load_stacks()
    table = tabulate(
        [
            [
                stack_name,
                stack["type"],
                stack["visibility"],
                stack["status"],
            ]
            for stack_name, stack in stacks.items()
        ],
        headers=headers,
        tablefmt="plain",
        numalign="left",
    )
    for line in table.splitlines():
        logger.info(line)


@click.command(options_metavar="[options]")
@click.argument("stack_path", metavar="<stack_path>")
@debug_option
def upload(stack_path):
    revision = CharmHub.upload(stack_path)
    if revision is not None:
        logger.info("uploaded revision {}.".format(revision))
    else:
        logger.info("no updates.")


@click.command()
@click.argument("name", metavar="<name>")
@click.option("--revision", "-r", metavar="<revision>", help="The revision to release")
@click.option("--channel", "-c", metavar="<channel>", help="The channel to release to")
@debug_option
def release(name, revision, channel):
    kwargs = {}
    if revision:
        kwargs["revision"] = revision
    if channel:
        kwargs["channel"] = channel
    revision, channel = CharmHub.release(name, **kwargs)
    logger.info(
        "stack {} released with revision {} to channel {}".format(
            name, revision, channel
        )
    )


def main():
    try:
        commands = [register, unregister, release, upload, names]
        for c in commands:
            cli.add_command(c)
        cli()
        exit(0)
    except Exception as e:
        logger.error(e)
    exit(1)


if __name__ == "__main__":
    main()
