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
python3 -m pip install .
```

Execute `juju-stack --help` to discover all the commands that the tool provides.

## Example

This section will guide you through the process of deploying a stack. The stack that we will deploy is k8s-based, but the tool support the deployment of a stack accross different clouds (both k8s- and machine-based).

First of all, we need to setup the Kubernetes cluster and bootstrap a Juju controller to it.

The prefered Kubernetes is Microk8s:

```bash
sudo snap install microk8s --classic
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

The stack we will be deploying is called `super-website-stack`, which is composed by two other components. A component can be a charm, or another stack. In this case, the two components that compose the website are two stacks: `mysql-stack` and `wordpress-stack`.

The reason why these two components are stacks, is because this example aims to showcase the ability of the stacks for deploying a multi-model scenario, being able to pass a configuration file to the deployment to place each component (stack) in a different model.

Let's get prepared for the deployment creating two models:

```bash
juju add-model database   # model for mysql-stack
juju add-model wordpress  # model for wordpress-stack
```

### juju-stack deploy

Now let's deploy the stack with the following command:

```bash
juju-stack deploy --config examples/super-website-config.yaml examples/super-website-stack super-website
```

### juju-stack status

The following command shows the status of the deployed stack instance.

```bash
juju-stack status super-website
```

## Stack specification

```yaml
# (Required) The name of the stack
name: <name>

# (Required) Short description of the stack
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

    # (Optional) Number of units for the application
    num_units: <num_units>

    # (Optional) Charm's key=value configuration. The charm configuration options available are particular for each individual charm. See `config.yaml` file in the charm.
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
    # (Required) Target endpoint of the provided endpoint.
    # It points to the actual component endpoint for the provided endpoint.
    #  <component name>: Name of the component in the current stack
    #  <endpoint name>: Name of the endpoint in the selected component
    #
    # Example:
    #   name: my-stack
    #   components:
    #     mysql:
    #       charm: ch:charmed-osm-mariadb-k8s
    #     wordpress:
    #       charm: ch:wordpress-k8s
    #   provides:
    #     forward: mysql:mysql
    #
    # Note: A `provides` endpoint can forward an endpoint of a stack, that itself forwards to a charm endpoint.
    forward: <component name>:<endpoint name>

# (Optional) Required endpoints by the current stack.
# These endpoints can be used to form relations by stacks that will include the current stack as a component.
requires:
  <requires endpoint name>:
    # (Required) Target endpoint of the required endpoint. It points to the actual component endpoint for the required endpoint. Same mechanism as in `provides:`.
    forward: <component name>:<endpoint name>

# (Optional) A list of the relations in the stack
relations:
  - # (Required) Provider endpoint of a component in this stack
    provider: <component name>:<endpoint name>

    # (Required) Requirer endpoint of a component in this stack
    requirer: <component name>:<endpoint name>
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
