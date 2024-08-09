import csv
import requests
from io import StringIO
from ipam.models import VLAN
from extras.scripts import Script

class CreateVLANs(Script):
    class Meta:
        name = "Create Layer 2 VLANs"
        description = "Create all Layer 2 VLANs based on a CSV file from GitHub"

    def run(self, data, commit):
        # Fetch the CSV from the GitHub URL
        url = 'https://raw.githubusercontent.com/EOS-ITS/Netbox-Scripts/main/vlans.csv'
        response = requests.get(url)
        csv_content = response.content.decode('utf-8')

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