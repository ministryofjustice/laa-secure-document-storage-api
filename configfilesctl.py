#!/usr/bin/env python3
import argparse
import os
import pathlib
from dataclasses import dataclass
from typing import List, Dict

from src.models.client_config import ClientConfig


@dataclass
class ConfigEntry:
    """
    Represents a ClientConfig and from whence it was loaded.
    """
    config: ClientConfig
    path: str


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
        config_path = os.path.join(config_dir, f"{client}.json")
        with open(config_path, 'w') as f:
            f.write(config.model_dump_json(indent=2))
        return ConfigEntry(config=config, path=config_path)


def print_config_entry(entry: ConfigEntry):
    print(f"## {entry.path}")
    print(entry.config.model_dump_json(indent=2))


def cmd_list(args: argparse.Namespace, **kwargs):
    source = ConfigSource()
    for config_entry in source.config_entries().values():
        print_config_entry(config_entry)


def cmd_find(args: argparse.Namespace, **kwargs):
    needle = args.needle
    source = ConfigSource()
    for config_entry in source.find_in_configs(needle):
        print_config_entry(config_entry)


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
    print_config_entry(config_entry)


def main():
    parser = argparse.ArgumentParser(description='Manage client configurations')
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand', required=True)

    list_parser = subparsers.add_parser('list', help='List all client configurations')
    list_parser.set_defaults(func=cmd_list)

    add_parser = subparsers.add_parser('add', help='Add a new client configuration')
    add_parser.add_argument('--client', type=str, default=None, help='Client name')
    add_parser.add_argument('--service_id', type=str, default=None, help='Service ID')
    add_parser.add_argument('--bucket_name', type=str, default=None, help='Bucket name')
    add_parser.add_argument(
        '--subdir', type=str, default=None,
        help='Optional subdirectory to store the configuration file'
    )
    add_parser.set_defaults(func=cmd_add)

    print_parser = subparsers.add_parser('find', help='Print client configurations containing the specified text')
    print_parser.add_argument('needle', type=str, help='String to find in client configuration values')
    print_parser.set_defaults(func=cmd_find)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
