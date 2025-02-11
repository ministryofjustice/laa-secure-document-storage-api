#!/usr/bin/env python3
import argparse
import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import List, Dict

from pydantic import BaseModel, Field

from src.models.client_config import ClientConfig


class ConfigEntry(BaseModel):
    """
    Represents a ClientConfig and from whence it was loaded.
    """
    config: ClientConfig = Field(description="The client configuration")
    path: str = Field(description="Path to the JSON file from which the configuration was loaded")


@dataclass
class ConfigSource:
    """
    Manages client configurations stored in JSON files rooted in `path` which defaults to the CONFIG_DIR environment
    variable.
    """
    path: str = os.getenv('CONFIG_DIR', 'clientconfigs')
    name: str = 'Config source'

    def config_entries(self) -> dict[str, ConfigEntry]:
        configs: Dict[str, ConfigEntry] = {}
        for config_path in pathlib.Path(self.path).rglob("*.json"):
            try:
                cfg_json = pathlib.Path(config_path).read_text()
                loaded_config = ClientConfig.model_validate_json(cfg_json)
                entry = ConfigEntry(config=loaded_config, path=str(config_path))
                configs[loaded_config.client] = entry
            except Exception as e:
                print(f"Error parsing {config_path}: {e}")
        return configs

    def client_exists(self, client: str) -> bool:
        return client in self.config_entries()

    def find_in_configs(self, needle: str) -> List[ConfigEntry]:
        config_entries = []
        for client, entry in self.config_entries().items():
            if client.find(needle) != -1 \
                    or entry.config.service_id.find(needle) != -1 \
                    or entry.config.bucket_name.find(needle) != -1:
                config_entries.append(entry)
        return config_entries

    def add_config(self, client: str, service_id: str, bucket_name: str, subdir: str | None = None) -> ConfigEntry:
        if self.client_exists(client):
            raise ValueError(f"Client {client} already exists")
        config = ClientConfig(client=client, service_id=service_id, bucket_name=bucket_name)
        config_dir = os.path.join(self.path, subdir) if subdir and subdir != '' else self.path
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        if os.path.isfile(config_dir):
            raise ValueError(f"Config directory {config_dir} is a file")
        config_path = os.path.join(config_dir, f"{client}.json")
        with open(config_path, 'w') as f:
            f.write(config.model_dump_json(indent=2))
        return ConfigEntry(config=config, path=config_path)


def print_config_entry(entry: ConfigEntry):
    print(entry.model_dump_json(indent=2))

def print_obj(obj: List[ConfigEntry] | ConfigEntry, sort_by_service: bool = True):
    if hasattr(obj, 'model_dump_json'):
        print(obj.model_dump_json(indent=2))
    else:
        if sort_by_service:
            config_by_service: Dict[str, List[ConfigEntry]] = {}
            for config_entry in obj:
                if config_entry.config.service_id not in config_by_service:
                    config_by_service[config_entry.config.service_id] = []
                config_by_service[config_entry.config.service_id].append(config_entry)
            print(json.dumps(config_by_service, indent=2, default=lambda x: x.model_dump()))
        else:
            print(json.dumps(obj, indent=2, default=lambda x: x.model_dump()))

def cmd_list(args: argparse.Namespace, **kwargs):
    source = ConfigSource()
    print_obj([c for c in source.config_entries().values()])


def cmd_find(args: argparse.Namespace, **kwargs):
    needle = args.needle
    source = ConfigSource()
    print_obj(source.find_in_configs(needle))


def cmd_get(args: argparse.Namespace, **kwargs):
    client = args.client
    source = ConfigSource()
    config_entries = source.config_entries()
    if args.client not in config_entries:
        raise ValueError(f"Client {client} not found")
    print_obj(config_entries[client])


def cmd_add(args: argparse.Namespace, **kwargs):
    client = args.client
    service_id = args.service_id
    bucket_name = args.bucket_name
    subdir = args.subdir

    # If any of the arguments are empty, interactively prompt for the value
    if client is None:
        client = input("Client name: ")
    if service_id is None:
        service_id = input("Service ID: ")
    if bucket_name is None:
        bucket_name = input("Bucket name: ")
    if subdir is None:
        subdir = input("Sub-directory (leave empty for no sub-directory): ")

    source = ConfigSource()
    config_entry = source.add_config(client, service_id, bucket_name, subdir=subdir)
    print_obj(config_entry)


def main():
    parser = argparse.ArgumentParser(description='Manage client configurations')
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand', required=True)

    list_parser = subparsers.add_parser('list', help='List all client configurations')
    list_parser.set_defaults(func=cmd_list)

    add_parser = subparsers.add_parser('add', help='Add a new client configuration')
    add_parser.add_argument('--client', type=str, default=None, help='Client name')
    add_parser.add_argument('--service-id', type=str, default=None, help='Service ID')
    add_parser.add_argument('--bucket-name', type=str, default=None, help='Bucket name')
    add_parser.add_argument(
        '--subdir', type=str, default=None,
        help='Optional subdirectory to store the configuration file'
    )
    add_parser.set_defaults(func=cmd_add)

    print_parser = subparsers.add_parser('find', help='Print client configurations containing the specified text')
    print_parser.add_argument('needle', type=str, help='String to find in client configuration values')
    print_parser.set_defaults(func=cmd_find)

    get_parser = subparsers.add_parser('get', help='Get a specific client configuration')
    get_parser.add_argument('client', type=str, help='Client name')
    get_parser.set_defaults(func=cmd_get)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValueError as ve:
        sys.stderr.write(f"{ve}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
