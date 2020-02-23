import yaml
import os
import inspect
from cerberus import Validator
import re


def read_yaml():
    """read config file for instructions"""
    with open("config.yml", 'r') as file1:
        yaml_file = yaml.safe_load(file1.read())
        # perform some checks
        v = Validator()
        v.schema = {'name': {'required': True, 'type': 'integer', 'min': 1, 'max': 10},
                    'looback': {'type': 'boolean'},
                    'external-looback': {'type': 'boolean'},
                    'p2p': {'type': 'list'},
                    'external-p2p': {'type': 'list'},
                    'lan': {'type': 'integer', 'min': 10, 'max': '255'},
                    'ospf': {'type': 'list'},
                    'eigrp': {'type': 'list'},
                    'ibgp': {'type': 'list'},
                    'ebgp': {'type': 'list'},
                    }
        for i in yaml_file:
            if not v.validate(i):
                print(v.errors)
                exit()
        return yaml_file


def generate_config():
    """generate config from config.yml"""
    blank_cfg = inspect.cleandoc('''!
        interface Gi1
        no shut
        !
        line con 0
         exec-timeout 0 0
         logging synchronous
         transport preferred none
        !
        ip tcp synwait-time 5
        no ip icmp rate-limit unreachable
        !
        no ip domain-lookup
        !''')

    yaml_file = read_yaml()
    for device in yaml_file:
        appended_cfg = blank_cfg + f'\nhostname R{device["name"]}\n!\n'

        if device.get('loopback'):
            loopback_ip = f'{device["name"]}.{device["name"]}.{device["name"]}.{device["name"]}'
            appended_cfg += f'interface loopback 0\n' \
                            f' ip address {loopback_ip} 255.255.255.255\n' \
                            f' ip ospf network point-to-point\n!\n'

        if device.get('external-loopback'):
            loopback_ip = f'20.{device["name"]}.{device["name"]}.{device["name"]}'
            appended_cfg += f'interface loopback 20\n' \
                            f' ip address {loopback_ip} 255.255.255.255\n' \
                            f' ip ospf network point-to-point\n!\n'

        if device.get('p2p'):
            for i in device['p2p']:
                dot1q = f'{device["name"]}{i}' if device["name"] < i else f'{i}{device["name"]}'  # make asc
                ip_address = f'10.0.{dot1q}.{device["name"]}'
                appended_cfg += f'interface gi1.{dot1q}\n' \
                                f' encapsulation dot1q {dot1q}\n' \
                                f' ip address {ip_address} 255.255.255.0\n' \
                                f' ip ospf network point-to-point\n!\n'

        if device.get('external-p2p'):
            for i in device['external-p2p']:
                dot1q = f'{device["name"]}{i}' if device["name"] < i else f'{i}{device["name"]}'  # make asc
                dot1q = 200 + int(dot1q)
                ip_address = f'20.0.{dot1q}.{device["name"]}'
                appended_cfg += f'interface gi1.{dot1q}\n' \
                                f' encapsulation dot1q {dot1q}\n' \
                                f' ip address {ip_address} 255.255.255.0\n' \
                                f' ip ospf network point-to-point\n!\n'

        if device.get('lan'):
                dot1q = f'{device["lan"]}'
                ip_address = f'10.0.{dot1q}.{device["name"]}'
                appended_cfg += f'interface gi1.{dot1q}\n' \
                                f' encapsulation dot1q {dot1q}\n' \
                                f' ip address {ip_address} 255.255.255.0\n!\n'

        if device.get('ospf'):
            appended_cfg += 'router ospf 1\n'
            for i in device['ospf']:
                if bool(re.search('loopback', str(i))):
                    network = f'{device["name"]}.{device["name"]}.{device["name"]}.{device["name"]}'
                elif bool(re.search('lan', str(i))):
                    network = f'10.0.{re.search("[0-9]+", i).group(0)}.{device["name"]}'
                else:
                    dot1q = f'{device["name"]}{i}' if device["name"] < i else f'{i}{device["name"]}'  # make asc
                    network = f'10.0.{dot1q}.{device["name"]}'
                appended_cfg += f' network {network} 0.0.0.0 area 0\n'
            appended_cfg += '!\n'

        if device.get('eigrp'):
            appended_cfg += 'router eigrp 1\n no auto-summary\n'
            for i in device['eigrp']:
                if bool(re.search('loopback', str(i))):
                    network = f'{device["name"]}.{device["name"]}.{device["name"]}.{device["name"]}'
                else:
                    dot1q = f'{device["name"]}{i}' if device["name"] < i else f'{i}{device["name"]}'  # make asc
                    network = f'10.0.{dot1q}.{device["name"]}'
                appended_cfg += f' network {network} 0.0.0.0\n'
            appended_cfg += '!\n'

        if device.get('ibgp'):
            appended_cfg += 'router bgp 1\n'
            for i in device['ibgp']:
                dot1q = f'{device["name"]}{i}' if device["name"] < i else f'{i}{device["name"]}'  # make asc
                neighbor = f'10.0.{dot1q}.{i}'
                appended_cfg += f' neighbor {neighbor} remote-as 1\n'
            appended_cfg += '!\n'

        if device.get('ebgp'):
            appended_cfg += f'router bgp {device["name"]}\n'
            for i in device['ebgp']:
                dot1q = f'{device["name"]}{i}' if device["name"] < i else f'{i}{device["name"]}'  # make asc
                neighbor = f'20.0.{dot1q}.{i}'
                appended_cfg += f' neighbor {neighbor} remote-as {i}\n'
            appended_cfg += '!\n'
        write_config(device['name'], appended_cfg)


def write_config(filename: str, dev_config: str):
    """write running device configuration to file"""
    if not os.path.exists('running'):
        os.mkdir('running')
    with open(f'running/{filename}', 'w') as output:
        output.write(dev_config)


def main():
    generate_config()


if __name__ == '__main__':
    main()