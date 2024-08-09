import csv
import requests
from io import StringIO
from ipam.models import VLAN
from dcim.models import Site
from extras.scripts import Script, StringVar, ObjectVar

class CreateVLANs(Script):
    class Meta:
        name = "Create Layer 2 VLANs"
        description = "Create all Layer 2 VLANs based on a CSV file from a specified URL"

    csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )

    site = ObjectVar(
        description="Select the site the VLANs will be assigned to",
        model=Site
    )

    def run(self, data, commit):
        url = data['csv_url']
        selected_site = data['site']

        # Fetch the CSV from the provided URL
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
            if not VLAN.objects.filter(vid=vlan_id, site=selected_site).exists():
                vlan = VLAN(vid=vlan_id, name=vlan_name, site=selected_site)
                vlan.save()
                self.log_success(f"Created VLAN {vlan_name} with ID {vlan_id} for site {selected_site.name}")
            else:
                self.log_warning(f"VLAN {vlan_name} with ID {vlan_id} already exists for site {selected_site.name}")

        self.log_info("Completed VLAN creation.")

