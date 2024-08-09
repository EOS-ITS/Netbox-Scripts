import csv
import requests
from io import StringIO
from ipam.models import VLAN
from extras.scripts import Script, StringVar

class CreateVLANs(Script):
    class Meta:
        name = "Create Layer 2 VLANs"
        description = "Create all Layer 2 VLANs based on a CSV file from a specified URL"

    csv_url = StringVar(
        description="Enter the URL of the CSV file containing VLAN IDs and names",
    )

    def run(self, data, commit):
        url = data['csv_url']

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
            vlan_id = int(row['vlan_id'])
            vlan_name = row['vlan_name']

            # Check if the VLAN already exists
            if not VLAN.objects.filter(vid=vlan_id).exists():
                vlan = VLAN(vid=vlan_id, name=vlan_name)
                vlan.save()
                self.log_success(f"Created VLAN {vlan_name} with ID {vlan_id}")
            else:
                self.log_warning(f"VLAN {vlan_name} with ID {vlan_id} already exists")

        self.log_info("Completed VLAN creation.")