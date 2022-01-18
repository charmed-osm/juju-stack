# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.
from enum import Enum
import subprocess
from typing import Any, Dict, List

from stack import COMPONENT_TYPES, STACK_SEPARATOR, StackData
from stack.charmhub import CharmHub
from stack.config import Config


class ResourceType(Enum):
    """Resource types that can be created in Juju"""

    CHARM = "charms"
    SAAS = "saas"
    OFFER = "offers"
    RELATION = "relation"


class Resource:
    """This class represents a Resource"""

    _created: bool = False

    def __init__(
        self,
        name: str,
        model: str,
        resource_type: ResourceType,
        create_command: List[str],
    ) -> None:
        """
        Args:
            resource_type: Type of the resource
            create_command: Command that needs to be executed to create the resource
        """
        self._create_command = create_command
        self._name = name
        self._model = model
        self._resource_type = resource_type

    @property
    def created(self) -> bool:
        """Boolean to check whether the resource has been created or not"""
        return self._created

    @property
    def name(self) -> str:
        """Returns the name of the resource"""
        return self._name

    @property
    def model(self) -> str:
        """Returns the model of the resource"""
        return self._model

    @property
    def type(self) -> ResourceType:
        """Type of the resource"""
        return self._resource_type

    def create(self) -> None:
        """
        Create the resource

        This function will execute the create command in order to create the resource.
        If the execution of the command success, then the `created` property will be set to True.

        Raises:
            subprocess.CalledProcessError: if the create_command execution fails
        """
        if not self.created:
            subprocess.run(self._create_command, check=True)
            self._created = True


class Plan:
    """
    This class represents a Plan

    A Plan is represented by a list of resources that need to be created.
    """

    def __init__(self) -> None:
        self._resources = []
        self._info = {}

    @property
    def resources(self) -> List[Resource]:
        """List of resources"""
        return self._resources

    def add_resource(self, resource: Resource):
        """Add resource to the plan"""
        self.resources.append(resource)

    def deploy(self) -> None:
        """
        Deploy plan

        This function will create all the resources of the plan in the order they were added.
        """
        for resource in self.resources:
            resource.create()
            model = resource.model
            if model not in self._info:
                self._info[model] = {
                    ResourceType.CHARM.value: [],
                    ResourceType.SAAS.value: [],
                    ResourceType.OFFER.value: [],
                }
            if resource.type != ResourceType.RELATION:
                self._info[model][resource.type.value].append(resource.name)

    def info(self) -> Dict[str, Any]:
        """Get information of the plan"""
        return self._info


class Component:
    """
    This class represents a component

    A stack is composed by components, where a component can be a charm, or another stack.
    """

    def __init__(
        self,
        parent: "Component" = None,
    ) -> None:
        """
        Args:
            parent: Parent component of the current component.
        """
        self._parent = parent

    @property
    def parent(self) -> "Component":
        """Parent component of the current component."""
        return self._parent

    @property
    def top_parent(self) -> "Component":
        """The top parent of the hierarchy of components"""
        current_component = self
        while current_component.parent is not None:
            current_component = current_component.parent
        return current_component

    @property
    def is_stack(self) -> bool:
        """Boolean to indicate if the Component is a Stack"""
        return isinstance(self, Stack)

    @property
    def is_charm(self) -> bool:
        """Boolean to indicate if the Component is a Charm"""
        return isinstance(self, Charm)

    @property
    def name(self) -> str:
        """
        Name of the component

        The returned output represents the name of the component
        taking into account the hierarchy of components.

        Example:
            sitersite.lma
        """
        name = []
        component = self
        while component.parent is not None:
            component_name = component.parent.get_component_name(component)
            name.insert(0, component_name)
            component = component.parent
        return STACK_SEPARATOR.join(name)

    def get_component_name(self, component: "Component") -> str:
        """
        Returns the name of a particular component

        Args:
            component: Component object
        """
        name = None
        if self.is_stack:
            for component_name, component_data in self.components.items():
                if component_data == component:
                    name = component_name
                    break
        return name


class Charm(Component):
    """Representation of a Charm Component"""

    def __init__(
        self,
        uri: str,
        config: Dict[str, Any],
        units: int = 1,
        channel: bool = None,
        trust: bool = False,
        parent: "Stack" = None,
    ) -> None:
        """
        Args:
            uri: Uri of the charm
            config: Config of the charm
            units: The number of units of the charm
            parent: Parent component of the charm. It must be a stack.
        """
        super().__init__(parent)
        self._uri = uri
        self._config = config
        self._units = units
        self._channel = channel
        self._trust = trust

    @property
    def uri(self) -> str:
        """Returns the uri of the charm"""
        return self._uri

    @property
    def config(self) -> Dict[str, Any]:
        """Returns a dictionary with the config of the charm"""
        return self._config

    @property
    def units(self) -> int:
        """Returns the number of units of the charm"""
        return self._units

    @property
    def trust(self) -> int:
        """Returns if the charm is trusted or not"""
        return self._trust

    @property
    def channel(self) -> int:
        """Returns the channel of the charm"""
        return self._channel


class Stack(Component):
    def __init__(
        self,
        stack_data: StackData,
        parent: "Stack" = None,
    ) -> None:
        super().__init__(parent)
        self.stack_name = stack_data.name
        self.data = stack_data
        self.description = self.data.description
        self._load_components()
        self._load_endpoints()
        self._load_relations()

    def __iter__(self):
        data = self.data.copy()
        for component_name in self.data.components.keys():
            if "stack" in data["components"][component_name]:
                data["components"][component_name] = dict(
                    self.components[component_name]
                )
        for key, value in data.items():
            yield key, value

    def _load_components(self):
        _components = {}
        for name, component_data in self.data.components.items():
            matched_types = [t for t in COMPONENT_TYPES if t in component_data]
            if len(matched_types) != 1:
                raise Exception(
                    "`charm` or `stack` must be present in the component data"
                )
            if matched_types[0] == "stack":
                stack_uri = component_data["stack"]
                stack = None
                if stack_uri.startswith(".") or "/" in stack_uri:
                    # Local stack
                    if not CharmHub._valid_path(stack_uri):
                        raise Exception(
                            "Not stack.yaml found in path {}.".format(stack_uri)
                        )
                    data = CharmHub._load_stack_yaml(stack_uri)
                    stack = Stack(data, self)
                else:
                    channel = component_data.get("channel", "stable")
                    data = CharmHub.get_stack(stack_uri, channel)
                    stack = Stack(data, self)
                _components[name] = stack
            else:
                _components[name] = Charm(
                    component_data["charm"],
                    component_data.get("config", {}),
                    component_data.get("units", 1),
                    component_data.get("channel"),
                    component_data.get("trust", False),
                    self,
                )
        self.components = _components

    def _load_endpoints(self):
        self.provides = {}
        self.requires = {}

        for name, endpoint_data in self.data.provides.items():
            forward_info = endpoint_data["forward"]
            component_name, endpoint_name = forward_info.split(":")
            component = self.components[component_name]
            if not component.is_stack:
                self.provides[name] = ProviderEndpoint(forward_info, self)
            else:
                self.provides[name] = component.provides[endpoint_name]

        for name, endpoint_data in self.data.requires.items():
            forward_info = endpoint_data["forward"]
            component_name, endpoint_name = forward_info.split(":")
            component = self.components[component_name]
            if not component.is_stack:
                self.requires[name] = RequirerEndpoint(forward_info, self)
            else:
                self.requires[name] = component.requires[endpoint_name]

    def _load_relations(self):
        self.relations = []
        for r in self.data.relations:
            provider_info = r["provider"]
            p_component_name, p_endpoint_name = provider_info.split(":")
            p_component = self.components[p_component_name]
            if not p_component.is_stack:
                provider_endpoint = ProviderEndpoint(provider_info, self)
            else:
                provider_endpoint = p_component.provides[p_endpoint_name]
            requirer_info = r["requirer"]
            r_component_name, p_endpoint_name = requirer_info.split(":")
            r_component = self.components[r_component_name]
            if not r_component.is_stack:
                requirer_endpoint = RequirerEndpoint(requirer_info, self)
            else:
                requirer_endpoint = r_component.requires[p_endpoint_name]
            relation = Relation(provider=provider_endpoint, requirer=requirer_endpoint)
            self.relations.append(relation)

    def get_plan(self, instance_name: str, config: Config):
        plan = Plan()
        for _, component in self.components.items():
            deployment_name = STACK_SEPARATOR.join([instance_name, component.name])
            if component.is_stack:
                component_plan = component.get_plan(instance_name, config)
                for r in component_plan.resources:
                    plan.add_resource(r)
            else:
                charm_resource = self.get_charm_resource(
                    component, deployment_name, config.get_model(self.name)
                )
                plan.add_resource(charm_resource)

        for relation in self.relations:
            provider_model = config.get_model(relation.provider.component.name)
            requirer_model = config.get_model(relation.requirer.component.name)
            provider_endpoint = (
                STACK_SEPARATOR.join(
                    [
                        instance_name,
                        relation.provider.component.name,
                        relation.provider.endpoint,
                    ]
                )
                if relation.provider.component.name
                else STACK_SEPARATOR.join([instance_name, relation.provider.endpoint])
            )
            requirer_endpoint = (
                STACK_SEPARATOR.join(
                    [
                        instance_name,
                        relation.requirer.component.name,
                        relation.requirer.endpoint,
                    ]
                )
                if relation.requirer.component.name
                else STACK_SEPARATOR.join([instance_name, relation.requirer.endpoint])
            )
            if provider_model != requirer_model:
                # offer
                offer_name = "{}{}{}{}{}".format(
                    instance_name,
                    STACK_SEPARATOR,
                    relation.provider.component.name,
                    STACK_SEPARATOR,
                    relation.provider.endpoint.replace(":", "-"),
                )
                offer_endpoint = "{}.{}{}{}{}{}".format(
                    provider_model,
                    instance_name,
                    STACK_SEPARATOR,
                    relation.provider.component.name,
                    STACK_SEPARATOR,
                    relation.provider.endpoint,
                )
                offer_uri = "{}.{}".format(provider_model, offer_name)
                offer_resource = self.get_offer_resource(
                    offer_endpoint, offer_name, provider_model
                )
                plan.add_resource(offer_resource)
                # consume
                saas_resource = self.get_saas_resource(
                    offer_uri, offer_name, requirer_model
                )
                plan.add_resource(saas_resource)
                provider_endpoint = offer_name
            relation_resource = self.get_relation_resource(
                provider_endpoint, requirer_endpoint, requirer_model
            )
            plan.add_resource(relation_resource)
        return plan

    def get_charm_resource(self, charm: Charm, name: str, model: str):
        resource_type = ResourceType.CHARM
        create_command = [
            "juju",
            "deploy",
            charm.uri,
            name,
            "-n",
            str(charm.units),
            "-m",
            model,
        ]
        if charm.channel:
            create_command.extend(["--channel", charm.channel])
        if charm.trust:
            create_command.append("--trust")
        for config_name, config_value in charm.config.items():
            create_command.append("--config")
            create_command.append("{}={}".format(config_name, config_value))
        return Resource(name, model, resource_type, create_command)

    def get_relation_resource(
        self, provider_endpoint: str, requirer_endpoint: str, model: str
    ):
        resource_type = ResourceType.RELATION
        create_command = [
            "juju",
            "relate",
            provider_endpoint,
            requirer_endpoint,
            "-m",
            model,
        ]
        return Resource(None, model, resource_type, create_command)

    def get_offer_resource(self, endpoint: str, offer_name: str, model: str):
        resource_type = ResourceType.OFFER
        create_command = ["juju", "offer", endpoint, offer_name]
        return Resource(
            endpoint.replace(":", "-"), model, resource_type, create_command
        )

    def get_saas_resource(self, offer_uri: str, saas_name: str, model: str):
        resource_type = ResourceType.SAAS
        create_command = ["juju", "consume", offer_uri, "-m", model]
        return Resource(saas_name, model, resource_type, create_command)


class Endpoint:
    """
    This class represents an endpoint

    The endpoint is formed by the name of the component and its endpoint name,
    joined by `:`. Example: \"mysql:db\"
    """

    def __init__(self, endpoint: str, component: Component) -> None:
        """
        Args:
            endpoint: String with the following format:
                        <component_name>:<component_endpoint_name>
            component: Object of the component associated to the endpoint
        """
        self._component = component
        self._endpoint = endpoint

    @property
    def component(self) -> Component:
        """Returns the component object associated to the endpoint"""
        return self._component

    @property
    def component_name(self) -> str:
        """Returns the name of the component associated to the endpoint"""
        return self.endpoint.split(":")[0]

    @property
    def endpoint_name(self) -> str:
        """Returns the endpoint name"""
        return self.endpoint.split(":")[1]

    @property
    def endpoint(self) -> str:
        """Returns the endpoint"""
        return self._endpoint


class ProviderEndpoint(Endpoint):
    """This class represents a Provider Endpoint"""

    def __init__(self, endpoint: str, component: Component) -> None:
        super().__init__(endpoint, component)


class RequirerEndpoint(Endpoint):
    """This class represents a Requirer Endpoint"""

    def __init__(self, endpoint: str, component: Component) -> None:
        super().__init__(endpoint, component)


class Relation:
    """
    This class represents a Relation

    A Relation is formed by two endpoints:
        - Provider: The endpoint that provides the service
        - Requirer: The endpoint that requires the service
    """

    def __init__(self, provider: ProviderEndpoint, requirer: RequirerEndpoint) -> None:
        """
        Args:
            provider: Provider endpoint of the relation
            requirer: Requirer endpoint of the relation
        """
        self.provider = provider
        self.requirer = requirer
