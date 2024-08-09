from extras.scripts import *
from django.utils.text import slugify

from dcim.choices import DeviceStatusChoices, SiteStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Site

class NewBranchScript(Script):

    class Meta:
        name = "New Branch"
        description = "Provision a new site"

    site_name = StringVar(
        description="Name of the new site"
    )
    core_switch_count = IntegerVar(
        description="Number of Core Switches to create"
    )
    core_switch_model = ObjectVar(
        description="Core Switch Model",
        model=DeviceType
    )
    access_switch_count = IntegerVar(
        description="Number of Access Switches to create"
    )
    access_switch_model = ObjectVar(
        description="Access Switch model",
        model=DeviceType
    )
    cabin_switch_count = IntegerVar(
        description="Number of Cabin Switches to create"
    )
    cabin_switch_model = ObjectVar(
        description="Cabin Switch Model",
        model=DeviceType
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

        # Create Access Switches
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

        # Create Cabin Switches
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

        # Generate a CSV table of new devices
        output = [
            'name,make,model'
        ]
        for device in Device.objects.filter(site=site):
            attrs = [
                device.name,
                device.device_type.manufacturer.name,
                device.device_type.model
            ]
            output.append(','.join(attrs))

        return '\n'.join(output)