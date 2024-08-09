import csv
from extras.scripts import *
from dcim.models import Site
from ipam.models import VLAN, VLANGroup
from django.utils.text import slugify

class CreateVLANsFromCSVScript(Script):

    class Meta:
        name = "Create VLANs from CSV"
        description = "Create VLAN groups and VLANs for a site from a CSV file"

    site = ObjectVar(
        description="Select the site",
        model=Site
    )
    vlan_group_name = StringVar(
        description="Name of the VLAN Group"
    )
    csv_file_path = StringVar(
        description="Path to the CSV file containing VLANs (relative to the script)"
    )

    def run(self, data, commit):

        # Create VLAN Group
        vlan_group = VLANGroup(
            name=data['vlan_group_name'],
            slug=slugify(data['vlan_group_name']),
            site=data['site']
        )
        vlan_group.save()
        self.log_success(f"Created VLAN Group: {vlan_group}")

        # Read VLANs from CSV
        csv_file = data['csv_file_path']
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                vlan_id = int(row['vlan_id'])
                vlan_name = row['name'].strip()
                vlan = VLAN(
                    vid=vlan_id,
                    name=vlan_name,
                    group=vlan_group,
                    site=data['site']
                )
                vlan.save()
                self.log_success(f"Created VLAN: {vlan}")

        # Generate a summary of created VLANs
        output = [
            'VLAN ID,Name,Group'
        ]
        for vlan in VLAN.objects.filter(group=vlan_group):
            attrs = [
                str(vlan.vid),
                vlan.name,
                vlan.group.name
            ]
            output.append(','.join(attrs))

        return '\n'.join(output)
