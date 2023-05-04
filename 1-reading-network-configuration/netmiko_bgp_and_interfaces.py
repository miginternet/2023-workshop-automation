# pip install --user textfsm
# pip install --user netmiko
import json
import netmiko
import ipaddress

bgp_md5_key = "foobar"
hosts = [
    {
        "host": "172.16.3.2",
        "device_type": "cisco_xr",
        "username": "clab",
        "password": "clab@123",
    },
    {
        "host": "172.16.3.3",
        "device_type": "cisco_xr",
        "username": "clab",
        "password": "clab@123",
    },
    {
        "host": "172.16.3.4",
        "device_type": "juniper_junos",
        "username": "clab",
        "password": "clab123",
    },
]


def main():
    result = {"hosts": []}

    for host in hosts:
        parsed_data = {}

        connection = netmiko.ConnectHandler(**host)

        try:
            if host["device_type"] == "cisco_xr":
                print(get_cisco_hostname(connection))
                print(get_cisco_version(connection))
                print(get_cisco_bgp_peers(connection, md5_key=bgp_md5_key))
                print(get_cisco_interfaces(connection))

            elif host["device_type"] == "juniper_junos":
                print(get_junos_hostname(connection))
                print(get_junos_version(connection))
                print(get_junos_bgp_peers(connection, md5_key=bgp_md5_key))
                print(get_junos_interfaces(connection))

            else:
                raise Exception(f"Device type {host['device_type']} not recognized.")

        except Exception:
            print(f"Errored on host: {host}!")
            raise
        finally:
            connection.disconnect()


def get_junos_hostname(connection: netmiko.ConnectHandler):
    output = json.loads(connection.send_command("show version | display json"))
    hostname = output["software-information"][0]["host-name"][0]["data"]
    return hostname


def get_junos_version(connection: netmiko.ConnectHandler):
    output = json.loads(connection.send_command("show version | display json"))
    version = output["software-information"][0]["junos-version"][0]["data"]
    return version


def get_junos_bgp_peers(connection: netmiko.ConnectHandler, md5_key=""):
    result = []
    bgp_data = json.loads(connection.send_command("show bgp neighbor | display json"))

    list_of_peers = bgp_data["bgp-information"][0]["bgp-peer"]

    for peer in list_of_peers:
        peer_ip_and_port = peer["peer-address"][0]["data"]
        ip = peer_ip_and_port.split("+")[0]
        result.append({"remote_address": ip, "md5_key": md5_key})

    return result


def get_junos_interfaces(connection: netmiko.ConnectHandler):
    result = []
    intf_data = json.loads(
        connection.send_command("show configuration interfaces | display json")
    )
    interfaces = intf_data["configuration"]["interfaces"]["interface"]
    for intf in interfaces:
        data = {
            "name": intf["name"],
            "description": intf["description"] if "description" in intf.keys() else "",
            "sub_ints": [],
        }
        for sub_int in intf["unit"]:
            name = sub_int["name"]
            description = (
                sub_int["description"] if "description" in sub_int.keys() else ""
            )
            vlan_id = sub_int["vlan-id"] if "vlan-id" in sub_int.keys() else ""

            # We will assume there is only a single IPv4 address configured.
            addr = sub_int["family"]["inet"]["address"][0]["name"]
            addr = ipaddress.ip_interface(addr)
            ip, mask = addr.with_netmask.split("/")
            data["sub_ints"].append(
                {
                    "name": name,
                    "description": description,
                    "vlan": vlan_id,
                    "ip_address": ip,
                    "subnet_mask": mask,
                }
            )
        result.append(data)

    return result


def get_cisco_hostname(connection: netmiko.ConnectHandler):
    output = connection.send_command("show run hostname").split()[-1]
    return output


def get_cisco_version(connection: netmiko.ConnectHandler):
    output = connection.send_command("show version | i ^ Version")
    return output.split()[-1]


def get_cisco_bgp_peers(connection: netmiko.ConnectHandler, md5_key=""):
    result = []
    bgp_neighbors = connection.send_command("show ip bgp summary", use_textfsm=True)
    for peer in bgp_neighbors:
        result.append({"remote_address": peer["bgp_neigh"], "md5_key": md5_key})
    return result


def get_cisco_interfaces(connection: netmiko.ConnectHandler):
    intf_data = connection.send_command("show interfaces", use_textfsm=True)
    return intf_data


if __name__ == "__main__":
    main()

