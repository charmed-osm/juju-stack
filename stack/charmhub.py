import os
import subprocess
from typing import Dict, NoReturn


from stack import CHARMHUB_CHANNELS, CHARMHUB_KEY, CHARMHUB_URI, JUJU_FOLDER, StackData
import yaml


def init() -> NoReturn:
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
        f.write(yaml.dump(stacks))


class CharmHub:
    @staticmethod
    def initialize():
        """Initialize CharmHub file"""
        init()

    @staticmethod
    def load_stacks() -> Dict:
        with open(CHARMHUB_URI, "r") as f:
            return yaml.safe_load(f)[CHARMHUB_KEY]

    @staticmethod
    def _save_stacks(stacks: Dict) -> NoReturn:
        file_content = None
        with open(CHARMHUB_URI, "r") as f:
            file_content = yaml.safe_load(f)
        if file_content is not None:
            file_content[CHARMHUB_KEY] = stacks
            with open(CHARMHUB_URI, "w") as f:
                f.write(yaml.dump(file_content))

    @staticmethod
    def register(name: str):
        """Register name in CharmHub"""
        if CharmHub.exists(name):
            raise Exception("name {} already exist.".format(name))
        CharmHub._register_name(name)

    @staticmethod
    def unregister(name: str):
        """Register name in CharmHub"""
        if not CharmHub.exists(name):
            raise Exception("name {} doesn't exist.".format(name))
        CharmHub._unregister_name(name)

    @staticmethod
    def upload(stack_path: str) -> int:
        """Upload stack"""
        if not CharmHub._valid_path(stack_path):
            raise Exception("Not stack.yaml found in path {}.".format(stack_path))
        stack = CharmHub._load_stack_yaml(stack_path)
        name = stack["name"]
        if not CharmHub.exists(name):
            raise Exception("name {} doesn't exist.".format(name))
        CharmHub._check_dependent_stacks(stack)
        return CharmHub._upload_stack(name, stack)

    @staticmethod
    def release(name: str, revision: int = None, channel: str = "stable"):
        """Release stack"""
        if not CharmHub.exists(name):
            raise Exception("name {} doesn't exist.".format(name))
        if not CharmHub.has_revision(name):
            raise Exception("upload a stack before releasing.")
        if revision and not CharmHub.has_revision(name, revision):
            raise Exception("revision {} does not exist.".format(revision))
        if not channel or channel not in CHARMHUB_CHANNELS:
            raise Exception("`{}` if not a valid value for channel".format(channel))
        if not revision:
            revision = CharmHub._get_latest_revision(name)
        CharmHub._release_stack(name, revision, channel)
        return (revision, channel)

    @staticmethod
    def get(name: str, channel: str = "stable"):
        """Return content of a stack"""
        if not CharmHub.exists(name):
            raise Exception("name {} doesn't exist.".format(name))
        if not channel or channel not in CHARMHUB_CHANNELS:
            raise Exception("`{}` if not a valid value for channel".format(channel))
        CharmHub.get_stack(name, channel)

    @staticmethod
    def has_revision(name, revision: int = None) -> bool:
        """Check if stack has a revision uploaded"""
        stacks = CharmHub.load_stacks()
        return (
            revision in stacks.get(name, {}).get("revisions", {})
            if revision
            else stacks.get(name, {}).get("latest-revision") >= 0
        )

    @staticmethod
    def exists(name: str) -> bool:
        """Check if name exists"""
        stacks = CharmHub.load_stacks()
        return name in stacks

    @staticmethod
    def get_stack(name: str, channel: str) -> StackData:
        """Get a stack from channel"""
        stacks = CharmHub.load_stacks()
        revision = stacks[name]["channels"][channel]
        return StackData(stacks[name]["revisions"][revision])

    @staticmethod
    def is_channel_active(name: str, channel: str):
        stacks = CharmHub.load_stacks()
        return stacks[name]["channels"][channel] >= 0

    @staticmethod
    def _check_dependent_stacks(stack: Dict):
        for component in stack.get("components", {}).values():
            if "stack" in component:
                stack_name = component["stack"]
                if not CharmHub.exists(stack_name):
                    raise Exception("name {} doesn't exist.".format(stack_name))
                channel = component.get("channel", "stable")
                if channel not in CHARMHUB_CHANNELS:
                    raise Exception("not valid channel `{}`".format(channel))
                if not CharmHub.is_channel_active(stack_name, channel):
                    raise Exception(
                        "not published stack in channel `{}`".format(channel)
                    )

    @staticmethod
    def _register_name(name):
        """Register a stack name"""
        stacks = CharmHub.load_stacks()
        stacks[name] = {
            "latest-revision": -1,
            "revisions": {},
            "channels": {channel: -1 for channel in CHARMHUB_CHANNELS},
            "visibility": "-",
            "type": "stack",
            "status": "unpublished",
        }
        CharmHub._save_stacks(stacks)

    @staticmethod
    def _unregister_name(name):
        """Unregister a stack name"""
        stacks = CharmHub.load_stacks()
        stacks.pop(name)
        CharmHub._save_stacks(stacks)

    @staticmethod
    def _valid_path(stack_path: str):
        """Check if stack path is valid"""
        return os.path.isfile("{}/stack.yaml".format(stack_path))

    @staticmethod
    def _load_stack_yaml(stack_path: str) -> Dict:
        """Load content of stack.yaml"""
        with open("{}/stack.yaml".format(stack_path), "r") as f:
            return yaml.safe_load(f)

    @staticmethod
    def _upload_stack(name: str, stack: Dict):
        """Upload a stack"""
        stacks = CharmHub.load_stacks()
        latest_revision = stacks[name]["latest-revision"]
        if latest_revision >= 0 and stack == stacks[name]["revisions"][latest_revision]:
            return
        revision = latest_revision + 1
        stacks[name]["revisions"][revision] = stack
        stacks[name]["latest-revision"] = revision
        CharmHub._save_stacks(stacks)
        return revision

    @staticmethod
    def _get_latest_revision(name: str):
        """Get latest revision number of a stack"""
        stacks = CharmHub.load_stacks()
        return stacks[name]["latest-revision"]

    @staticmethod
    def _release_stack(name: str, revision: int, channel: str):
        """Release a stack revision to a channel"""
        stacks = CharmHub.load_stacks()
        stacks[name]["channels"][channel] = revision
        stacks[name]["visibility"] = "Public"
        stacks[name]["status"] = "published"
        CharmHub._save_stacks(stacks)
