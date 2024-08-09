from extras.scripts import *
from django.utils.text import slugify
from dcim.models import Site

class SimpleScript(Script):

    class Meta:
        name = "Simple Test Script"
        description = "A simple script to test loading functionality."

    site_name = StringVar(
        description="Name of the new site"
    )

    def run(self, data, commit):
        # Basic log output for testing
        self.log_info(f"Running script for site: {data['site_name']}")

        # Simple site creation for testing
        site = Site(
            name=data['site_name'],
            slug=slugify(data['site_name']),
            status='planned'
        )
        site.save()
        self.log_success(f"Created new site: {site.name}")
