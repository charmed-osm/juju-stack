<!-- Copyright 2021 Canonical Ltd.
See LICENSE file for licensing details. -->

# juju-stack

## Quickstart

### Requirements

- Python3 versions supported: >=3.6

Install `juju-stack` with the following commands:

```bash
# Clone the juju-stack repository
git clone https://github.com/davigar15/juju-stack
cd juju-stack/

# Install juju-stack
sudo apt update && sudo apt install python3-pip -y
python3 -m pip install .
```

Execute `juju-stack --help` to discover all the commands that the tool provides.

> Note: Make sure $HOME/.local/bin is included in your PATH.
>
> ```bash
> $ echo PATH=$PATH:$HOME/.local/bin | tee -a ~/.bashrc
> $ source ~/.bashrc
> ```

## Example

This section will guide you through the process of deploying a stack. The stack that we will deploy is k8s-based, but the tool support the deployment of a stack accross different clouds (both k8s- and machine-based).

First of all, we need to setup the Kubernetes cluster and bootstrap a Juju controller to it.

The prefered Kubernetes is Microk8s:

```bash
sudo snap install microk8s --classic --channel 1.21/stable
sudo usermod -a -G microk8s `whoami`
sudo chown -f -R `whoami` ~/.kube
newgrp microk8s
microk8s.status --wait-ready  # wait for microk8s to start
microk8s.enable storage dns ingress  # enable needed plugins for juju
```

Now let's install the `juju` snap and bootstrap a Juju controller in Microk8s:

```bash
sudo snap install juju --classic
juju bootstrap microk8s
```

Change to the directory where the files for the examples live.

```bash
cd examples/
```

In order to have a prototype that is extremely close to what it will look like when it is actually implemented in juju, we have included a `charmcraft-stack` command to publish the stacks to a mock CharmHub.

Let's register, upload and publish all the stacks.

```bash
stacks="website lma website-lma"
for stack in $stacks; do
  charmcraft-stack register $stack
  charmcraft-stack upload $stack/
  charmcraft-stack release $stack
done
```

The stack we will be deploying is called `web-lma-stack`, which is composed by two other components. A component can be a charm, or another stack. In this case, the two components that compose the website are two stacks: `website-stack` and `lma-stack`.

This example aims to showcase the ability of placing stacks in different models, by passing an instantiation file.

First, we will deploy all the stack in one model.

```bash
juju add-model all-in-one
juju-stack deploy website-lma supersite
```

Wait for the deployment to settle: `watch -c juju-stack status supersite`.

Now we will deploy the same stack but with a configuration file, placing some components in different models.

```bash
juju add-model web
juju add-model lma
juju-stack deploy --config supersite.yaml website-lma d-supersite
```

Wait for the deployment to settle: `watch -c juju-stack status d-supersite`.

To remove the deployments execute the following commands:

```bash
juju-stack destroy supersite
juju-stack destroy d-supersite
```

## Stack specification

```yaml
# (Required) The name of the stack
name: <name>

# (Optional) Short description of the stack
description: <description>

# (Required) A list of components that are part of the current stack.
# There are two types of components: charms and stacks.
components:
  <component name>:
    # (Required) Path of the component.
    # The <component type> has two possible values:
    #  - `stack` if the component is a stack
    #  - `charm` if the component if a charm.
    #
    # Example:
    #   stack: ./path/to/the/stack
    #   charm: ./path/to/the/charm
    <component type>: <path>

    # The following keys are optional and only valid for charm-type components

    # (Optional) Number of units of the application
    units: <units>

    # (Optional) Whether the component is trusted or not
    trust: <boolean>

    # (Optional) Channel of the charm in CharmHub
    channel: <channel>

    # (Optional) Charm's key=value configuration.
    # The charm configuration options available are particular for each individual charm.
    # See `config.yaml` file in the charm.
    #
    # Example:
    #   config:
    #     some-option: foo
    #     port: 80
    config: <config>

# (Optional) Provided endpoints by the current stack.
# These endpoints can be used to form relations by stacks that will include the current stack as a component.
provides:
  <provides endpoint name>:
    # (Required) Target endpoint of the provides.
    # It points to the actual component endpoint for the provides.
    #  <component name>: Name of the component in the current stack
    #  <endpoint name>: Name of the endpoint in the selected component
    #
    # Example:
    #   name: my-stack
    #   components:
    #     database:
    #       charm: ch:charmed-osm-mariadb-k8s
    #     wordpress:
    #       charm: ch:wordpress-k8s
    #   provides:
    #     forward: database:mysql  # where `mysql` is the endpoint in the `database` component.
    #
    # Note: A `provides` endpoint can forward an endpoint of a stack, that itself forwards to a charm endpoint.
    forward: <component name>:<endpoint name>

# (Optional) Required endpoints by the current stack.
# These endpoints can be used to form relations by stacks that will include the current stack as a component.
requires:
  <requires endpoint name>:
    # (Required) Target endpoint of the requires.
    #  It points to the actual component endpoint for the requires.
    # Same mechanism as in `provides:`.
    forward: <component name>:<endpoint name>

# (Optional) A list of the relations in the stack
relations:
  - # (Required) Provider endpoint of a component in this stack
    provider: <component name>:<endpoint name>

    # (Required) Requirer endpoint of a component in this stack
    requirer: <component name>:<endpoint name>
```

### Config specification

The `juju-stack deploy` command has the `--config <path_to_config>` option to set a configuration file that will be used at instantiation.

The main purpose of this file is to distribute the a stack across models. By default, the whole stack will be deployed in the current model. Optionally, the config file can be used to place `sub-stacks` in different models.

This is the config file specification:

```yaml
# (Optional) Default model for the deployment
default-model: <default model>

components:
  # (Optional) Component name to which the config inside should be applied to.
  # To select components that are inside a stack component, use "." to join the two (or more)
  # components.
  #
  # Example:
  #   components:
  #     db: {...}
  #     lma.prometheus: {...}
  <component name>:
    # (Optional) Model name to which the component will be deployed.
    # This option is only available for a stack component.
    # The model set to a stack gets, by default, inherited by its child components,
    # unless specified by another configuration in the config file.
    model: <model name>
```

## Develop

The recommended way of installing the `juju-stack` tool for developers is in a virtual environment. Make sure you have the package `python3-venv` installed. If you don't, execute the following command:

```bash
sudo apt update
sudo apt install python3-venv -y
```

Now let's install `juju-stack`

```bash
# Clone the juju-stack repository
git clone https://github.com/davigar15/juju-stack
cd juju-stack/

# Create a virtualenv and install juju-stack
python3 -m venv venv
source venv/bin/activate
python3 -m pip install .
```

Execute `juju-stack --help` to discover all the commands that the tool provides.
