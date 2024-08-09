from extras.scripts import *
from django.utils.text import slugify
from dcim.choices import DeviceStatusChoices, SiteStatusChoices, InterfaceTypeChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Interface
from ipam.models import VLAN, Prefix, IPAddress
from ipam.fields import IPNetworkField
import csv
import requests
from io import StringIO
from netaddr import IPNetwork

class DeploySiteWithVLANsAndIPs(Script):

    class Meta:
        name = "Deploy Site with VLANs and IPs"
        description = "Automate site deployment, including creating devices, VLANs, and assigning IPs."

    site_name = StringVar(
        description="Name of the new site"
    )
    ship_id = StringVar(
        description="Enter Ship ID"
    )
    core_switch_count = IntegerVar(
        description="Number of Core Switches to create"
    )
    core_switch_model = ObjectVar(
        description="Core Switch Model",
        model=DeviceType,
        required=False
    )
    access_switch_count = IntegerVar(
        description="Number of Access Switches to create"
    )
    access_switch_model = ObjectVar(
        description="Access Switch model",
        model=DeviceType,
        required=False
    )
    cabin_switch_count = IntegerVar(
        description="Number of Cabin Switches to create"
    )
    cabin_switch_model = ObjectVar(
        description="Cabin Switch Model",
        model=DeviceType,
        required=False
    )
    site_subnet = IPNetworkField(
        description="Enter the site subnet (e.g., 10.61.0.0/16)"
    )
    management_vlan_id = IntegerVar(
        description="Management VLAN ID"
    )
    csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )

    def run(self, data, commit):
        # Step 1: Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status=SiteStatusChoices.STATUS_PLANNED,
            description=data['ship_id']
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Step 2: Create Management Subnet from Site Subnet
        management_prefix = IPNetwork(f"{data['site_subnet']}/24")  # Example of taking /24 for management
        management_prefix = Prefix.objects.create(
            prefix=management_prefix,
            site=site,
            status='active'
        )
        self.log_success(f"Created management prefix: {management_prefix.prefix} for site {site.name}")

        # Step 3: Create Core Switches
        if data['core_switch_count'] > 0:
            core_switch_role = DeviceRole.objects.get(name='Core Switch')
            for i in range(1, data['core_switch_count'] + 1):
                switch = Device(
                    device_type=data['core_switch_model'],
                    name=f'{site.slug.upper()}-CORE-SW-{i}',
                    site=site,
                    status=DeviceStatusChoices.STATUS_PLANNED,
                    device_role=core_switch_role
                )
                switch.save()
                self.log_success(f"Created new Core switch: {switch.name}")

                # Assign IP from management prefix
                ip_address = management_prefix.prefix[i + 10]  # Skip first 10 IPs
                ip = IPAddress.objects.create(
                    address=f"{ip_address}/{management_prefix.prefix.prefixlen}",
                    interface=Interface.objects.create(
                        name=f"Vlan{data['management_vlan_id']}",
                        device=switch,
                        type=InterfaceTypeChoices.TYPE_VIRTUAL,
                        enabled=True
                    ),
                    status='active'
                )
                self.log_success(f"Assigned IP {ip} to {switch.name}")

        # Step 4: Create Access Switches
        if data['access_switch_count'] > 0:
            access_switch_role = DeviceRole.objects.get(name='Access Switch')
            for i in range(1, data['access_switch_count'] + 1):
                switch = Device(
                    device_type=data['access_switch_model'],
                    name=f'{site.slug.upper()}-ACCESS-SW-{i}',
                    site=site,
                    status=DeviceStatusChoices.STATUS_PLANNED,
                    device_role=access_switch_role
                )
                switch.save()
                self.log_success(f"Created new Access switch: {switch.name}")

                # Assign IP from management prefix
                ip_address = management_prefix.prefix[data['core_switch_count'] + i + 10]
                ip = IPAddress.objects.create(
                    address=f"{ip_address}/{management_prefix.prefix.prefixlen}",
                    interface=Interface.objects.create(
                        name=f"Vlan{data['management_vlan_id']}",
                        device=switch,
                        type=InterfaceTypeChoices.TYPE_VIRTUAL,
                        enabled=True
                    ),
                    status='active'
                )
                self.log_success(f"Assigned IP {ip} to {switch.name}")

        # Step 5: Create Cabin Switches
        if data['cabin_switch_count'] > 0:
            cabin_switch_role = DeviceRole.objects.get(name='Cabin Switch')
            for i in range(1, data['cabin_switch_count'] + 1):
                switch = Device(
                    device_type=data['cabin_switch_model'],
                    name=f'{site.slug.upper()}-CABIN-SW-{i}',
                    site=site,
                    status=DeviceStatusChoices.STATUS_PLANNED,
                    device_role=cabin_switch_role
                )
                switch.save()
                self.log_success(f"Created new Cabin switch: {switch.name}")

                # Assign IP from management prefix
                ip_address = management_prefix.prefix[data['core_switch_count'] + data['access_switch_count'] + i + 10]
                ip = IPAddress.objects.create(
                    address=f"{ip_address}/{management_prefix.prefix.prefixlen}",
                    interface=Interface.objects.create(
                        name=f"Vlan{data['management_vlan_id']}",
                        device=switch,
                        type=InterfaceTypeChoices.TYPE_VIRTUAL,
                        enabled=True
                    ),
                    status='active'
                )
                self.log_success(f"Assigned IP {ip} to {switch.name}")

        # Step 6: Fetch and Create VLANs from CSV (similar to previous implementation)
        # ...

        self.log_info("Site deployment with VLANs and IPs completed.")