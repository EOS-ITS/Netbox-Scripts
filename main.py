import csv
import requests
from io import StringIO
from ipam.models import VLAN

class NewBranchScript(Script):

    class Meta:
        name = "New Branch with VLANs"
        description = "Provision a new site with core switches and VLANs"

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
    csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )

    def run(self, data, commit):

        # Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status=SiteStatusChoices.STATUS_PLANNED
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Create Core Switches
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

        # Fetch the CSV from the provided URL
        url = data['csv_url']
        try:
            response = requests.get(url)
            response.raise_for_status()
            csv_content = response.content.decode('utf-8')
        except requests.exceptions.RequestException as e:
            self.log_failure(f"Failed to fetch the CSV file: {e}")
            return

        # Read the CSV content
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
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

        self.log_info("Core switches and VLANs created successfully.")
