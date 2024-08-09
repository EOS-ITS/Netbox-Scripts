import csv
import requests
from io import StringIO
from dcim.models import Device
from ipam.models import VLAN, VLANGroup
from extras.scripts import Script

class CreateVLANs(Script):
    class Meta:
        name = "Create VLANs and Assign to Group"
        description = "Create VLANs and assign them to a VLAN Group from a CSV file"

    vlan_group_name = "Default Group"  # Name of your VLAN Group

    def fetch_vlans_from_github(self, url):
        response = requests.get(url)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)
        return list(reader)

    def run(self, data, commit):
        vlans = self.fetch_vlans_from_github('https://github.com/EOS-ITS/Netbox-Scripts/blob/main/vlans.csv')

        # Get or create the VLAN group
        vlan_group, created = VLANGroup.objects.get_or_create(name=self.vlan_group_name)
        
        for vlan_data in vlans:
            vlan_id = int(vlan_data['vlan_id'])
            vlan_name = vlan_data['vlan_name']
            
            # Create the VLAN and assign it to the group
            vlan, created = VLAN.objects.get_or_create(
                vid=vlan_id,
                name=vlan_name,
                group=vlan_group
            )
            self.log_info(f"VLAN {vlan_id} - {vlan_name} created and added to group {self.vlan_group_name}")

        self.log_success("All VLANs created successfully.")

# End of script
