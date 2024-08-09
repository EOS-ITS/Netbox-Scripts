from extras.scripts import *
from django.utils.text import slugify
from dcim.choices import DeviceStatusChoices, SiteStatusChoices, InterfaceTypeChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Interface, Region, SiteGroup
from extras.models import ConfigTemplate
from ipam.models import VLAN, Prefix
import csv
import requests
from io import StringIO

class DeploySiteWithVLANs(Script):

    class Meta:
        name = "Deploy Site"
        description = "Automate site deployment, including creating devices, VLANs, prefixes, and virtual interfaces."

    ship_name = StringVar(
        description="Name of the new site"
    )
    ship_id = StringVar(
        description="Enter Ship ID",
        required=False
    )
    ship_region = ObjectVar(
        description="Select the region for the site",
        model=Region,
        required=False
    )
    ship_group = ObjectVar(
        description="Select the site group for the site",
        model=SiteGroup,
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
    core_switch_template = ObjectVar(
        description="Select the configuration template for Core Switches",
        model=ConfigTemplate,
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
    access_switch_template = ObjectVar(
        description="Select the configuration template for Access Switches",
        model=ConfigTemplate,
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
    cabin_switch_template = ObjectVar(
        description="Select the configuration template for Cabin Switches",
        model=ConfigTemplate,
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
            name=data['ship_name'],
            slug=slugify(data['ship_name']),
            status=SiteStatusChoices.STATUS_PLANNED,
            description=data['ship_id'] if data['ship_id'] else None,
            region=data['ship_region'],
            group=data['ship_group']
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

        # Step 3: Function to create switches, assign their management interfaces, and apply templates
        def create_switches(switch_count, switch_model, switch_role, switch_type, switch_template):
            for i in range(1, switch_count + 1):
                switch_name = f'{site.slug.upper()}-{switch_type}-SW-{i}'
                switch = Device(
                    device_type=switch_model,
                    name=switch_name,
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

                # Apply configuration template if selected
                if switch_template:
                    try:
                        rendered_config = switch_template.render(context={'device': switch})
                        switch.config_context = rendered_config
                        switch.save()
                        self.log_success(f"Applied {switch_template.name} to {switch.name}")
                    except Exception as e:
                        self.log_failure(f"Failed to apply configuration template for {switch.name}: {e}")

        # Step 4: Create Core Switches
        if data['core_switch_count'] > 0:
            core_switch_role = DeviceRole.objects.get(name='Core Switch')
            create_switches(
                switch_count=data['core_switch_count'], 
                switch_model=data['core_switch_model'], 
                switch_role=core_switch_role, 
                switch_type="CORE",
                switch_template=data.get('core_switch_template')
            )

        # Step 5: Create Access Switches
        if data['access_switch_count'] > 0:
            access_switch_role = DeviceRole.objects.get(name='Access Switch')
            create_switches(
                switch_count=data['access_switch_count'], 
                switch_model=data['access_switch_model'], 
                switch_role=access_switch_role, 
                switch_type="ACCESS",
                switch_template=data.get('access_switch_template')
            )

        # Step 6: Create Cabin Switches
        if data['cabin_switch_count'] > 0:
            cabin_switch_role = DeviceRole.objects.get(name='Cabin Switch')
            create_switches(
                switch_count=data['cabin_switch_count'], 
                switch_model=data['cabin_switch_model'], 
                switch_role=cabin_switch_role, 
                switch_type="CABIN",
                switch_template=data.get('cabin_switch_template')
            )

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
