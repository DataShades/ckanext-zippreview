import os

import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckanext.zippreview.helpers import get_helpers

_formats = ["zip", "application/zip", "application/x-zip-compressed"]


class ZipPreviewPlugin (p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IResourceView, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=False)

    # IConfigurer
    def update_config(self, config):
        tk.add_template_directory(config, "templates")
        tk.add_public_directory(config, "public")
        tk.add_resource("public", "ckanext-zippreview")

    # ITemplateHelpers
    def get_helpers(self):
        return get_helpers()

    # IResourceView
    def info(self):
        return {
            "name": "zip_view",
            "title": "ZIP Viewer",
            "default_title": "ZIP Viewer",
            "icon": "folder-open"
        }

    def can_view(self, data_dict):
        resource = data_dict["resource"]
        format_lower = resource.get("format", "").lower()
        if (format_lower == ""):
            format_lower = os.path.splitext(resource["url"])[1][1:].lower()
        
        if format_lower in _formats:
            return True
        return False

    def view_template(self, context, data_dict):
        return "zip.html"
