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
        name = "Deploy Site"
        description = "Automate site deployment, including creating devices, VLANs, prefixes, and virtual interfaces."

    site_name = StringVar(
        description="Name of the new site"
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

        # Add additional logic here if this loads successfully

