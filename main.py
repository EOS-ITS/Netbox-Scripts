from extras.scripts import *
from django.utils.text import slugify
from dcim.choices import DeviceStatusChoices, SiteStatusChoices, InterfaceTypeChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Interface
from ipam.models import VLAN, Prefix
from ipam.fields import IPNetworkField
import csv
import requests
from io import StringIO

class DeploySite(Script):

    class Meta:
        name = "Deploy Site"
        description = "Automate site deployment, including management VLAN, prefixes, and VLANs from a CSV file."

    site_name = StringVar(
        description="Name of the new site"
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
    vlan_id = IntegerVar(
        description="VLAN ID for Management Interface"
    )
    management_prefix = IPNetworkField(
        description="Management Prefix (e.g., 192.168.1.0/24)"
    )
    csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )

    def run(self, data, commit):
        # Step 1: Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status=SiteStatusChoices.STATUS_PLANNED
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Step 2: Create the management prefix
        prefix = Prefix(
            prefix=data['management_prefix'],
            site=site,
            status='active',
        )
        prefix.save()
        self.log_success(f"Created management prefix: {prefix.prefix} for site {site.name}")

        # Step 3: Create the Management VLAN
        management_vlan = VLAN(
            vid=data['vlan_id'],
            name=f"Management VLAN {data['vlan_id']}",
            site=site
        )
        management_vlan.save()
        self.log_success(f"Created Management VLAN {management_vlan.vid} for site {site.name}")

        # Step 4: Fetch and Create VLANs from CSV
        try:
            response = requests.get(data['csv_url'])
            response.raise_for_status()
            csv_content = response.content.decode('utf-8')
            reader = csv.DictReader(StringIO(csv_content))
            for row in reader:
                self.log_info(f"Processing row: {row}")
                row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
                try:
                    vlan_id = int(row['vlan_id'])
                    vlan_name = row['vlan_name']
                except KeyError as e:
                    self.log_failure(f"Missing expected column in CSV: {e}")
                    continue
                except ValueError as e:
                    self.log_failure(f"Invalid VLAN ID value: {e}")
                    continue

                if not VLAN.objects.filter(vid=vlan_id, site=site).exists():
                    vlan = VLAN(vid=vlan_id, name=vlan_name, site=site)
                    vlan.save()
                    self.log_success(f"Created VLAN {vlan_name} with ID {vlan_id} for site {site.name}")
                else:
                    self.log_warning(f"VLAN {vlan_name} with ID {vlan_id} already exists for site {site.name}")
        except requests.exceptions.RequestException as e:
            self.log_failure(f"Failed to fetch the CSV file: {e}")
            return

        # Step 5: Function to create switches and their management interfaces
        def create_switches(switch_count, switch_model, switch_role, switch_type):
            for i in range(1, switch_count + 1):
                switch = Device(
                    device_type=switch_model,
                    name=f'{site.slug.upper()}-{switch_type}-SW-{i}',
                    site=site,
                    status=DeviceStatusChoices.STATUS_PLANNED,
                    device_role=switch_role
                )
                switch.save()
                self.log_success(f"Created new {switch_type} switch: {switch.name}")

                # Create virtual interface for the management VLAN
                interface = Interface(
                    name=f"Vlan{data['vlan_id']}",
                    device=switch,
                    type=InterfaceTypeChoices.TYPE_VIRTUAL,
                    enabled=True
                )
                interface.save()
                self.log_success(f"Created virtual interface {interface.name} on {switch.name}")

        # Step 6: Create Core Switches
        if data['core_switch_count'] > 0:
            core_switch_role = DeviceRole.objects.get(name='Core Switch')
            create_switches(data['core_switch_count'], data['core_switch_model'], core_switch_role, "CORE")

        # Step 7: Create Access Switches
        if data['access_switch_count'] > 0:
            access_switch_role = DeviceRole.objects.get(name='Access Switch')
            create_switches(data['access_switch_count'], data['access_switch_model'], access_switch_role, "ACCESS")

        # Step 8: Create Cabin Switches
        if data['cabin_switch_count'] > 0:
            cabin_switch_role = DeviceRole.objects.get(name='Cabin Switch')
            create_switches(data['cabin_switch_count'], data['cabin_switch_model'], cabin_switch_role, "CABIN")

        self.log_info("Site deployment completed.")
