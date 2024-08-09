import csv
import urllib.request
from io import StringIO
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
    csv_file_url = StringVar(
        description="URL to the CSV file containing VLANs"
    )

    def run(self, data, commit):

        # Create VLAN Group
        vlan_group = VLANGroup(
            name=data['vlan_group_name'],
            slug=slugify(data['vlan_group_name'])
        )
        vlan_group.save()
        self.log_success(f"Created VLAN Group: {vlan_group}")

        # Download CSV file from URL using urllib
        try:
            with urllib.request.urlopen(data['csv_file_url']) as response:
                csv_content = response.read().decode('utf-8')
        except Exception as e:
            self.log_failure(f"Failed to download CSV file: {e}")
            return

        # Read VLANs from CSV content
        reader = csv.DictReader(StringIO(csv_content))

        # Debugging: Print the detected headers
        detected_headers = reader.fieldnames
        self.log_info(f"Detected Headers: {detected_headers}")

        if detected_headers is None:
            self.log_failure("No headers detected. Check the CSV format.")
            return

        # Mapping headers manually if there's an issue
        header_map = {header.lower().strip(): header for header in detected_headers}
        if 'vlan_id' not in header_map:
            self.log_failure(f"'vlan_id' header not found in detected headers: {detected_headers}")
            return
        if 'name' not in header_map:
            self.log_failure(f"'name' header not found in detected headers: {detected_headers}")
            return

        for row in reader:
            self.log_info(f"Processing row: {row}")
            vlan_id = int(row[header_map['vlan_id']].strip())
            vlan_name = row[header_map['name']].strip()
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
