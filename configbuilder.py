#!/usr/bin/env python3
import argparse
import inspect
import json
import os
import pathlib
import sys
from typing import List, Dict, Any, Tuple

from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

from src.models.client_config import ClientConfig
from src.models.file_validator_spec import FileValidatorSpec
from src.validation.file_validator import FileValidator

# Suppress verbose and distracting logging from casbin and other modules, then import app for introspecting routes
os.environ['LOGGING_LEVEL_CASBIN'] = 'ERROR'
os.environ['LOGGING_LEVEL_ROOT'] = 'ERROR'
from src.main import app  # noqa: E402


def generate_all_filevalidatorspecs() -> List[FileValidatorSpec]:
    all_specs = []
    for validator in FileValidator.__subclasses__():
        validator_kwargs = get_kwargs_for_filevalidator(validator)
        all_specs.append(FileValidatorSpec(name=validator.__name__, validator_kwargs=validator_kwargs))
    return all_specs


def generate_recommended_filevalidatorspecs() -> List[FileValidatorSpec]:
    return [
        FileValidatorSpec(
            name='DisallowedFileExtensions',
            validator_kwargs={'extensions': ['', ]}
        ),
        FileValidatorSpec(
            name='DisallowedMimetypes',
            validator_kwargs={
                'content_types': [
                    'application/x-sh', 'text/x-sh', 'application/x-msdownload', 'application/x-msdos-program'
                ]
            }
        )
    ]


def get_kwargs_for_filevalidator(validator: str | FileValidator) -> Dict[str, Any]:
    if isinstance(validator, str):
        for validator_cls in FileValidator.__subclasses__():
            if validator_cls.__name__ == validator:
                validator = validator_cls
                break
    if not hasattr(validator, 'validate'):
        raise ValueError(f"Validator {validator} does not have a 'validate' method")
    # Introspect the 'validate' method to get any expected extra arguments which need to appear in the spec
    validator_args = [a for a in inspect.getfullargspec(validator.validate).args if a not in ('self', 'file_object')]
    validator_defaults = inspect.getfullargspec(validator.validate).defaults
    validator_kwargs = {}
    for i, arg in enumerate(validator_args):
        try:
            value = validator_defaults[i]
            if value is list:
                value = []
        except ValueError:
            value = None
        validator_kwargs[arg] = value
    return validator_kwargs


class PolicyItem(BaseModel):
    """
    An individual permission, from which a casbin policy rule can be generated.
    """
    path: str = Field(description="The route")
    action: str = Field(description="The action")

    @classmethod
    def generate_from_app(cls) -> List['PolicyItem']:
        """
        Inspects the main application object to generate a list of PolicyItems from the API routes registered to the
        application.

        :return:
        """
        policy_items: List['PolicyItem'] = []
        for route in app.routes:
            if isinstance(route, APIRoute):
                policy_items.append(cls(path=route.path, action=','.join(route.methods)))
        return policy_items


class ClientAcl(BaseModel):
    """
    Encapsulates a single file of casbin policy rules for a single client.
    """
    azure_client_id: str = Field(description="The client name")
    policy_items: List[PolicyItem] = Field(description="The policy items")

    @classmethod
    def generate(cls, azure_client_id: str) -> 'ClientAcl':
        return ClientAcl(
            azure_client_id=azure_client_id,
            policy_items=[]
        )

    @classmethod
    def load_from_csv(cls, file_obj):
        policy_items = []
        azure_client_id = None
        for line in file_obj:
            # Ignore comments
            if line.startswith('#'):
                continue
            # Split the line into parts, stripping whitespace and newlines
            parts = [p.strip() for p in line.split(',')]
            # Collect the client ID from the first line
            if azure_client_id is None:
                azure_client_id = parts[1]
            if len(parts) == 4 and parts[1] == azure_client_id:
                policy_items.append(PolicyItem(path=parts[2], action=parts[3]))
        return cls(azure_client_id=azure_client_id, policy_items=policy_items)

    def write(self, file_obj):
        for policy_item in self.policy_items:
            file_obj.write(f"p, {self.azure_client_id}, {policy_item.path}, {policy_item.action}\n")


class ClientBundle(BaseModel):
    """
    Represents a directory for a single client, named after the Azure display name, and containing a ClientConfig and
    a CSV ACL file, with the files named after the client ID.
    """
    azure_client_id: str = Field(description="The Azure application (client) ID, used for naming the files")
    azure_display_name: str = Field(
        description="The Azure display name (used for logging and directory name)", default=None
    )
    service_name: str = Field(description="The repo or cloud platform name (used as common directory for clients)",)

    bundle_path: str = Field(description="The path to the client bundle", default=None)
    clientconfig_path: str = Field(description="The path to the client configuration file", default=None)
    clientacl_path: str = Field(description="The path to the client ACL file", default=None)

    clientconfig: ClientConfig = Field(description="The client configuration", default=None)
    clientacl: ClientAcl = Field(description="The client ACL", default=None)

    @classmethod
    def load_azureclientids(cls) -> List[str]:
        """
        Iterate through all directories in the CONFIG_DIR directory, looking for a single JSON file in each. If found,
        we assume the child directory contains a client config and acl, and treat it as a clientbundle.
        :return:
        """
        azure_client_ids = []
        bundles_dir = os.getenv('CONFIG_DIR', 'clientconfigs')
        candidates: List[pathlib.Path] = [p for p in pathlib.Path(bundles_dir).rglob("*.json")]
        for candidate in candidates:
            azure_client_id = os.path.splitext(os.path.basename(candidate))[0]
            azure_client_ids.append(azure_client_id)
        return azure_client_ids

    @classmethod
    def load_clientbundle(cls, azure_client_id: str) -> 'ClientBundle':
        """
        Load a single client bundle by client ID
        :param azure_client_id: The client ID
        :return: The client bundle
        """
        bundles_dir = os.getenv('CONFIG_DIR', 'clientconfigs')
        bundle = None
        candidates: List[pathlib.Path] = [p for p in pathlib.Path(bundles_dir).rglob(f"{azure_client_id}*.json")]
        # Should ony have one config file per client
        if len(candidates) == 1:
            candidate = candidates[0]
            bundle_dir = os.path.abspath(candidate.parent)
            azure_display_name = candidate.parent.name
            service_name = candidate.parent.parent.name
            # We may have been given a fragment of an ID, so take the full ID from the filename
            azure_client_id = os.path.splitext(os.path.basename(candidates[0]))[0]
            config_path = str(candidates[0])
            acl_path = os.path.join(bundle_dir, f"{azure_client_id}.csv")
            bundle = cls(
                azure_client_id=azure_client_id, service_name=service_name, azure_display_name=azure_display_name,
                bundle_path=bundle_dir, clientconfig_path=config_path, clientacl_path=acl_path
            )
            bundle.get_or_create()
        else:
            print(f"Found an unexpected number ({len(candidates)}) of configs in {bundles_dir} for {azure_client_id}")
        return bundle

    @classmethod
    def load_clientbundles(cls) -> List['ClientBundle']:
        clientbundles = []
        for azure_client_id in cls.load_azureclientids():
            bundle = cls.load_clientbundle(azure_client_id)
            if bundle is not None:
                clientbundles.append(bundle)
        return clientbundles

    def get_bundle_path(self):
        if self.bundle_path is None:
            self.bundle_path = os.path.join(
                os.getenv('CONFIG_DIR', 'clientconfigs'), self.service_name, self.azure_display_name
            )
        return self.bundle_path

    def get_clientconfig_path(self) -> str:
        if self.clientconfig_path is None:
            self.clientconfig_path = os.path.join(self.get_bundle_path(), f"{self.azure_client_id}.json")
        return self.clientconfig_path

    def get_clientacl_path(self) -> str:
        if self.clientacl_path is None:
            self.clientacl_path = os.path.join(self.get_bundle_path(), f"{self.azure_client_id}.csv")
        return self.clientacl_path

    def create_bundlepath(self):
        bundle_path = self.get_bundle_path()
        if not os.path.exists(bundle_path):
            os.makedirs(bundle_path)
        return bundle_path

    def get_or_create(self) -> 'ClientBundle':
        self.get_or_create_clientconfig()
        self.get_or_create_clientacl()
        return self

    def write(self, overwrite: bool = False):
        self.write_clientconfig(overwrite)
        self.write_clientacl(overwrite)
        return self

    def find(self, sub: str) -> bool:
        searchable_fields = [
            self.azure_client_id, self.azure_display_name, self.clientconfig.bucket_name, self.service_name
        ]
        for field in searchable_fields:
            if field.find(sub) != -1:
                return True
        return False

    def get_or_create_clientconfig(self, bucket_name: str = None) -> ClientConfig:
        if self.clientconfig is None:
            if self.clientconfig_path is None:
                self.clientconfig_path = self.get_clientconfig_path()
            if os.path.exists(self.clientconfig_path):
                # Config already exists, so load
                with open(self.clientconfig_path, 'r') as f:
                    self.clientconfig = ClientConfig.model_validate_json(f.read())
                # Ensure display name is set from the config file, as it may have defaulted to the service name
                self.azure_display_name = self.clientconfig.azure_display_name
            else:
                # Config does not exist, so create
                self.clientconfig = ClientConfig(
                    azure_client_id=self.azure_client_id,
                    azure_display_name=self.azure_display_name,
                    bucket_name=bucket_name if bucket_name is not None else f"{self.azure_display_name}-bucket",
                    file_validators=generate_recommended_filevalidatorspecs()
                )
        return self.clientconfig

    def get_or_create_clientacl(self) -> ClientAcl:
        if self.clientacl is None:
            if self.clientacl_path is None:
                self.clientacl_path = self.get_clientacl_path()
            if os.path.exists(self.clientacl_path):
                # ACL already exists, so load
                with open(self.clientacl_path, 'r') as f:
                    self.clientacl = ClientAcl.load_from_csv(f)
            else:
                # ACL does not exist, so create
                self.clientacl = ClientAcl.generate(self.azure_client_id)
                # Add ACL line for bucket
                self.clientacl.policy_items.append(
                    PolicyItem(path=self.get_or_create_clientconfig().bucket_name, action='(CREATE)|(READ)')
                )
        return self.clientacl

    def write_clientconfig(self, overwrite: bool = False):
        self.create_bundlepath()
        clientconfig_path = self.get_clientconfig_path()
        if os.path.exists(clientconfig_path) and not overwrite:
            raise ValueError(f"Client configuration file {clientconfig_path} already exists")
        with open(clientconfig_path, 'w') as f:
            f.write(self.clientconfig.model_dump_json(indent=2))
        return self.clientconfig

    def write_clientacl(self, overwrite: bool = False):
        self.create_bundlepath()
        clientacl_path = self.get_clientacl_path()
        if os.path.exists(clientacl_path) and not overwrite:
            raise ValueError(f"Client ACL file {clientacl_path} already exists")
        with open(clientacl_path, 'w') as f:
            self.clientacl.write(f)
        return self.clientacl


def print_obj(obj: ClientBundle | List | Dict):
    if hasattr(obj, 'model_dump_json'):
        print(obj.model_dump_json(indent=2))
    else:
        print(json.dumps(obj, indent=2, default=lambda x: x.model_dump()))


def prompt_for_value(prompt: str, current: str, deletable: bool = False) -> str | None:
    response = input(
        f"{prompt}, current '{current}': Accept" + (", Edit or Delete? [A/e/d]" if deletable else " or Edit? [A/e]")
    )
    if response.lower() == 'e':
        new_value = input("New value: ")
        # Pressing return with no value is treated as keep the current value
        if new_value not in (None, ''):
            return new_value
    elif response.lower() == 'd':
        return None
    return current


def interactive_edit(
            bundle: ClientBundle,
            edit_client: bool = True,
            edit_acl: bool = True,
            edit_validators: bool = True,
        ):
    if edit_client:
        print("=== Client Configuration ===")
        # Client ID and service name are not editable, add a new client instead
        bundle.azure_display_name = prompt_for_value("Azure display name", bundle.azure_display_name)
        bundle.clientconfig.bucket_name = prompt_for_value("Bucket name", bundle.clientconfig.bucket_name)

    # Don't edit lists in-place, batch the removes for later
    removes: List[Tuple[list, Any]] = []

    if edit_acl:
        print("=== Client ACL ===")
        all_routes = PolicyItem.generate_from_app()
        all_routes.append(PolicyItem(path=bundle.clientconfig.bucket_name, action="(CREATE)|(READ)"))
        cmd = input(
            f"Currently using {len(bundle.clientacl.policy_items)} routes out of {len(all_routes)}. "
            f"Edit {len(bundle.clientacl.policy_items)}, accept, or select from {len(all_routes)}? [E/a/s] "
        ).lower()
        if cmd == 'a':
            pass
        else:
            if cmd == 's':
                # Reset, then edit
                bundle.clientacl.policy_items = all_routes
            for policy_item in bundle.clientacl.policy_items:
                edited_path = prompt_for_value("Resource", policy_item.path, deletable=True)
                if edited_path is None:
                    removes.append((bundle.clientacl.policy_items, policy_item))
                    continue
                policy_item.path = edited_path
                policy_item.action = prompt_for_value(f" ↳ Action on {policy_item.path}", policy_item.action)

    if edit_validators:
        print("=== Client File Filters ===")
        all_specs = generate_all_filevalidatorspecs()
        cmd = input(
            f"Currently using {len(bundle.clientconfig.file_validators)} file filters out of {len(all_specs)}. "
            f"Edit {len(bundle.clientconfig.file_validators)}, accept, or select from {len(all_specs)}? [E/a/s] "
        ).lower()
        if cmd == 'a':
            pass
        else:
            if cmd == 's':
                # Reset, then edit
                bundle.clientconfig.file_validators = all_specs
            for validator_spec in bundle.clientconfig.file_validators:
                keep = input(f"Filter using {validator_spec.name}? [Y/n] ") not in ('n', 'N')
                if not keep:
                    removes.append((bundle.clientconfig.file_validators, validator_spec))
                    continue
                new_kwargs = {}
                for arg, value in validator_spec.validator_kwargs.items():
                    new_kwargs[arg] = prompt_for_value(f" ↳ {validator_spec.name} parameter {arg}", value)
                    if isinstance(value, list) and isinstance(new_kwargs[arg], str):
                        new_kwargs[arg] = new_kwargs[arg].split(' ')
                validator_spec.validator_kwargs = new_kwargs

    for item_list, item in removes:
        item_list.remove(item)
    return bundle


def cmd_list(args: argparse.Namespace, **kwargs):
    # List azure client ids and their display names sorted by service name (parent dir), then display name
    output: List[Dict[str, str]] = []
    for bundle in ClientBundle.load_clientbundles():
        output.append({
            'azure_client_id': bundle.azure_client_id, 'azure_display_name': bundle.azure_display_name,
            'service_name': bundle.service_name
        })
    print_obj(sorted(output, key=lambda x: x['azure_display_name']))


def cmd_find(args: argparse.Namespace, **kwargs):
    sub = args.sub
    bundles = [b for b in ClientBundle.load_clientbundles() if b.find(sub)]
    print_obj(bundles)


def cmd_get(args: argparse.Namespace, **kwargs):
    azure_client_id = args.azure_client_id
    bundle = ClientBundle.load_clientbundle(azure_client_id)
    print_obj(bundle)


def cmd_add(args: argparse.Namespace, **kwargs):
    # If any of the arguments are empty, interactively prompt for the value
    azure_client_id = args.azure_client_id if args.azure_client_id not in (None, '') \
        else input("Azure application (client) ID: ")
    azure_display_name = args.azure_display_name if args.azure_display_name not in (None, '') \
        else input("Azure display name: ")
    bucket_name = args.bucket_name if args.bucket_name not in (None, '') \
        else input("Bucket name: ")
    service_name = args.service_name if args.service_name not in (None, '') \
        else input("Service name: ")

    client_bundle = ClientBundle(
        azure_client_id=azure_client_id, azure_display_name=azure_display_name, service_name=service_name
    )
    client_bundle.get_or_create_clientconfig(bucket_name)
    client_bundle.get_or_create_clientacl()
    interactive_edit(client_bundle, edit_client=False)
    client_bundle.write()


def cmd_edit(args: argparse.Namespace, **kwargs):
    azure_client_id = args.azure_client_id
    bundle = ClientBundle.load_clientbundle(azure_client_id)
    if bundle is None:
        raise ValueError(f"Client {azure_client_id} not found")
    interactive_edit(bundle)
    bundle.write(overwrite=True)
    print_obj(bundle)


def main():
    parser = argparse.ArgumentParser(description='Manage client configurations')
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand', required=True)

    list_parser = subparsers.add_parser('list', help='List all client configurations')
    list_parser.set_defaults(func=cmd_list)

    print_parser = subparsers.add_parser('find', help='Print client configurations containing the specified text')
    print_parser.add_argument('sub', type=str, help='Sub-string to find in client configuration values')
    print_parser.set_defaults(func=cmd_find)

    get_parser = subparsers.add_parser('get', help='Get a specific client configuration')
    get_parser.add_argument('azure_client_id', type=str, help='Azure client ID, or start of ID')
    get_parser.set_defaults(func=cmd_get)

    edit_parser = subparsers.add_parser('edit', help='Edit a specific client configuration')
    edit_parser.add_argument('azure_client_id', type=str, help='Azure client ID, or start of ID')
    edit_parser.set_defaults(func=cmd_edit)

    add_parser = subparsers.add_parser('add', help='Add a new client configuration with ACL and file ')
    add_parser.add_argument('--azure-client-id', type=str, default=None, help='Azure client ID')
    add_parser.add_argument('--azure-display-name', type=str, default=None, help='Used for labelling and logging')
    add_parser.add_argument('--service-name', type=str, help='CP or repo name of application using the client')
    add_parser.add_argument('--bucket-name', type=str, default=None, help='Bucket name')
    add_parser.set_defaults(func=cmd_add)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as ve:
        sys.stderr.write(f"{ve}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
