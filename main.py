from extras.scripts import *
from django.utils.text import slugify
from dcim.choices import DeviceStatusChoices, SiteStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site
from ipam.models import VLAN, Prefix
import csv
import requests
from io import StringIO

class DeploySiteWithVLANs(Script):

    class Meta:
        name = "Deploy Site with VLANs"
        description = "Automate site deployment, including creating devices, VLANs, and assigning a prefix."

    site_name = StringVar(
        description="Name of the new site"
    )
    ship_id = StringVar(
        description="Enter Ship ID"
    )
    prefix = StringVar(
        description="Enter the IP prefix for the site (e.g., 192.168.1.0/24)"
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
    csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )

    def run(self, data, commit):
        # Step 1: Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            description=f"Ship ID: {data['ship_id']}",
            status=SiteStatusChoices.STATUS_PLANNED
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Step 2: Create the prefix for the site
        site_prefix = Prefix(
            prefix=data['prefix'],
            site=site,
            status='active'  # You can customize the status if needed
        )
        site_prefix.save()
        self.log_success(f"Created IP prefix {site_prefix.prefix} for site {site.name}")

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
                self.log_success(f"Created new Core switch: {switch}")

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
                self.log_success(f"Created new Access switch: {switch}")

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
                self.log_success(f"Created new Cabin switch: {switch}")

        # Step 6: Fetch and Create VLANs from CSV
        url = data['csv_url']
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
