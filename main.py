from extras.scripts import *
from django.utils.text import slugify
from dcim.choices import DeviceStatusChoices, SiteStatusChoices, InterfaceTypeChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Interface
from ipam.models import VLAN, Prefix
import csv
import requests
from io import StringIO

class DeploySiteWithVLANs(Script):

    class Meta:
        name = "Deploy Site with VLANs"
        description = "Automate site deployment, including creating devices, VLANs, prefixes, and virtual interfaces."

    site_name = StringVar(
        description="Name of the new site"
    )
    ship_id = StringVar(
        description="Enter Ship ID",
        required=False
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
    vlan_csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )
    management_vlan_id = IntegerVar(
        description="Enter the VLAN ID for the Management Interface (e.g., 188)"
    )
    site_prefix = StringVar(
        description="Enter the CIDR for the site prefix (e.g., 192.168.0.0/24)"
    )

    def run(self, data, commit):
        # Step 1: Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status=SiteStatusChoices.STATUS_PLANNED,
            description=data['ship_id'] if data['ship_id'] else None
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Step 2: Create a prefix for the site
        prefix = Prefix.objects.create(
            prefix=data['site_prefix'],
            site=site,
            status='active'
        )
        self.log_success(f"Created prefix {prefix} for site {site.name}")

        # Step 3: Function to create switches and their management interfaces
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

                # Create virtual interface for the Management VLAN
                interface_name = f"Vlan{data['management_vlan_id']}"
                interface = Interface(
                    name=interface_name,
                    device=switch,
                    type=InterfaceTypeChoices.TYPE_VIRTUAL,
                    enabled=True
                )
                interface.save()
                self.log_success(f"Created virtual interface {interface.name} on {switch.name}")

        # Step 4: Create Core Switches
        if data['core_switch_count'] > 0:
            core_switch_role = DeviceRole.objects.get(name='Core Switch')
            create_switches(data['core_switch_count'], data['core_switch_model'], core_switch_role, "CORE")

        # Step 5: Create Access Switches
        if data['access_switch_count'] > 0:
            access_switch_role = DeviceRole.objects.get(name='Access Switch')
            create_switches(data['access_switch_count'], data['access_switch_model'], access_switch_role, "ACCESS")

        # Step 6: Create Cabin Switches
        if data['cabin_switch_count'] > 0:
            cabin_switch_role = DeviceRole.objects.get(name='Cabin Switch')
            create_switches(data['cabin_switch_count'], data['cabin_switch_model'], cabin_switch_role, "CABIN")

        # Step 7: Fetch and Create VLANs from CSV
        url = data['vlan_csv_url']
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            csv_content = response.content.decode('utf-8')
        except requests.exceptions.RequestException as e:
            self.log_failure(f"Failed to fetch the CSV file: {e}")
            return

        # Read the CSV content
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
            # Output the row for debugging
            self.log_info(f"Processing row: {row}")

            # Normalize the keys by stripping whitespace and converting to lower case
            row = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}

            # Safely access the VLAN ID and VLAN name
            try:
                vlan_id = int(row['vlan_id'])
                vlan_name = row['vlan_name']
            except KeyError as e:
                self.log_failure(f"Missing expected column in CSV: {e}")
                continue
            except ValueError as e:
                self.log_failure(f"Invalid VLAN ID value: {e}")
                continue

            # Check if the VLAN already exists in the selected site
            if not VLAN.objects.filter(vid=vlan_id, site=site).exists():
                vlan = VLAN(vid=vlan_id, name=vlan_name, site=site)
                vlan.save()
                self.log_success(f"Created VLAN {vlan_name} with ID {vlan_id} for site {site.name}")
            else:
                self.log_warning(f"VLAN {vlan_name} with ID {vlan_id} already exists for site {site.name}")

        self.log_info("Completed VLAN creation for the site.")
