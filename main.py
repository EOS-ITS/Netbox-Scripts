from extras.scripts import *
from django.utils.text import slugify
from dcim.choices import DeviceStatusChoices, SiteStatusChoices, InterfaceTypeChoices
from dcim.models import Device, DeviceRole, DeviceType, Site, Interface
from ipam.models import VLAN, Prefix
from ipam.fields import IPNetworkField

class DeploySite(Script):
    
    class Meta:
        name = "Deploy Site"
        description = "Automate site deployment including VLANs, management prefix, and virtual interfaces."

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

    def run(self, data, commit):
        # Create the new site
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status=SiteStatusChoices.STATUS_PLANNED
        )
        site.save()
        self.log_success(f"Created new site: {site}")

        # Create the management prefix
        prefix = Prefix(
            prefix=data['management_prefix'],
            site=site,
            status='active',
            role=None  # You can set a role if you have predefined roles in NetBox
        )
        prefix.save()
        self.log_success(f"Created management prefix: {prefix.prefix} for site {site.name}")

        # Create the VLAN for the management interface
        vlan = VLAN(
            vid=data['vlan_id'],
            name=f"VLAN{data['vlan_id']}",
            site=site
        )
        vlan.save()
        self.log_success(f"Created VLAN {vlan.vid} for site {site.name}")

        # Function to create switches and their management interfaces
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

        # Create Core Switches
        if data['core_switch_count'] > 0:
            core_switch_role = DeviceRole.objects.get(name='Core Switch')
            create_switches(data['core_switch_count'], data['core_switch_model'], core_switch_role, "CORE")

        # Create Access Switches
        if data['access_switch_count'] > 0:
            access_switch_role = DeviceRole.objects.get(name='Access Switch')
            create_switches(data['access_switch_count'], data['access_switch_model'], access_switch_role, "ACCESS")

        # Create Cabin Switches
        if data['cabin_switch_count'] > 0:
            cabin_switch_role = DeviceRole.objects.get(name='Cabin Switch')
            create_switches(data['cabin_switch_count'], data['cabin_switch_model'], cabin_switch_role, "CABIN")

        self.log_info("Site deployment completed.")
