import yaml
import os
import inspect
from cerberus import Validator
import re
from multiprocessing import Process
import shutil
import telnetlib
import sys
import time

new_run = True
blank_cfg = inspect.cleandoc('''!
        configure terminal
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
IP = '148.251.122.103'
START_PORT = 2100
AVAILABLE_DEVICES = 2


def read_yaml():
    """read config file for instructions"""
    with open("config.yml", 'r') as file1:
        yaml_file = yaml.safe_load(file1.read())
        # perform some checks
        v = Validator()
        v.schema = {'name': {'required': True, 'type': 'integer', 'min': 1, 'max': 10},
                    'loopback': {'type': 'boolean'},
                    'external-looback': {'type': 'boolean'},
                    'p2p': {'type': 'list'},
                    'external-p2p': {'type': 'list'},
                    'lan': {'type': 'integer', 'min': 100, 'max': '255'},
                    'ospf': {'type': 'list'},
                    'eigrp': {'type': 'list'},
                    'ibgp': {'type': 'list'},
                    'ebgp': {'type': 'list'},
                    }
        for i in yaml_file:
            if not v.validate(i):
                print(v.errors)
                exit()
        if len(yaml_file) > AVAILABLE_DEVICES:
            print(f'topology ({len(yaml_file)}) is bigger than the number of available devices ({AVAILABLE_DEVICES})')
        return yaml_file


def load_template():
    """load templates from running/*.yml to config.yml
    templates must contain word topology else won't be shown"""
    yaml_files = [f.path for f in os.scandir('templates') if f.name.endswith('.yml')]
    templates = {}
    option = 0
    for i in yaml_files:
        with open(i, 'r') as file1:
            topology = re.search('topology.*', file1.read(), flags=re.MULTILINE|re.DOTALL)
            if topology:
                option += 1
                templates[option] = i
                print(f'OPTION {option}:{re.sub("# |topology", "", topology.group(0))}')
    while True:
        selected = input(f'which  option to load? <1-{option}> ')
        if selected.isdigit() and (int(selected) in range(1, option)):
            shutil.copy(templates[int(selected)], 'config.yml')
            print('updated config.yml file')
            break


def generate_config():
    """generate config from config.yml"""
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
        appended_cfg += 'end'
        write_config(device['name'], appended_cfg)
    print('running-config generated')


def write_config(filename: str, dev_config: str):
    """write running device configuration to file"""
    global new_run
    if new_run:
        if not os.path.exists('running'):
            os.mkdir('running')
        else:
            for file in os.scandir('running'):
                os.unlink(file.path)
        new_run = False
    with open(os.path.join('running', f'R{filename}'), 'w') as output:
        output.write(dev_config)


def get_config(file):
    """used by telnet_to"""
    try:
        with open(file.path) as myfile:
            return myfile.read()
    except Exception as e:
        print(e)


def telnet_to(port, config=None):
    try:
        # restore base config
        if not config:
            print(f"loading startup-config for R{port - START_PORT}")
            tn = telnetlib.Telnet(IP, port)
            tn.write('end\n'.encode('ascii'))
            time.sleep(0.2)
            tn.write('config replace nvram:startup-config force\n'.encode('ascii'))
            time.sleep(1)
            tn.close()

        # load provided config
        else:
            print(f"loading running-config for R{port-START_PORT}")
            tn = telnetlib.Telnet(IP, port)
            for i in config.split('!'):
                tn.write(i.encode('ascii'))
                time.sleep(0.2)
            tn.write('\n'.encode('ascii'))
            tn.close()

    except Exception as e:
        print(f'Exception on device R{port - START_PORT} ({port}):\n\t{e}')
        sys.exit()


def load_running_config():
    processes = list()
    for file in os.scandir('running'):
        try:
            port = int(re.search('[0-9]+', file.name).group(0)) + START_PORT
            processes.append(Process(target=telnet_to, args=(port, get_config(file))))
        except Exception as e:
            print(e)

    for p in processes:
        p.start()
    [p.join() for p in processes]


def load_ine_running_config():
    if AVAILABLE_DEVICES < 10:
        print(f'Minimum of 10 devices are required to load the labs. Currently have {AVAILABLE_DEVICES}')
        sys.exit()
    chosen_config = input('Specify INE workbook name (i.e basic eigrp routing or basic.eigrp.routing): ').replace(" ", ".").lower()
    config_path = os.path.join('ine.ccie.rsv5.workbook.initial.configs', 'advanced.technology.labs', chosen_config)

    if not os.path.exists(config_path):
        print(f'directory ine.ccie.rsv5.workbook.initial.configs/advanced.technology.labs/{chosen_config} doesn\'t exist')
        sys.exit()

    processes = list()
    for file in os.scandir(config_path):
        try:
            port = re.split('r|\.', file.name.lower())[1]
            port = START_PORT + int(port)
            processes.append(Process(target=telnet_to, args=(port, get_config(file))))
        except Exception as e:
            print(f"skipping non-router entry - {file.name}")

    for p in processes:
        p.start()
    [p.join() for p in processes]


def delete_running_config():
    processes = list()
    for port in range(START_PORT+1, AVAILABLE_DEVICES+1):
        processes.append(Process(target=telnet_to, args=(port,)))

    for p in processes:
        p.start()
    [p.join() for p in processes]


def get_user_action():
    """get user action"""
    global new_run
    while True:
        new_run = True
        action = input("\nOptions:\n"
                       "1. create running from config.yml\n"
                       "2. create running from template\n"
                       "3. load config to devices\n"
                       "4. erase running-config from devices\n"
                       "5. load INE advanced.technology.labs v5 to devices\n"
                       "Select option: ")
        if '1' in action:
            generate_config()
        elif '2' in action:
            load_template()
            generate_config()
        elif '3' in action:
            load_running_config()
            break
        elif '4' in action:
            delete_running_config()
        elif '5' in action:
            load_ine_running_config()
            break


def main():
    get_user_action()


if __name__ == '__main__':
    main()
