from future import standard_library
standard_library.install_aliases()
    
import requests
import zipfile
import struct
import sys
import logging
import re
import urllib
import six

from io import StringIO
from collections import OrderedDict

from ckan.lib import uploader, formatters


log = logging.getLogger(__name__)


def get_helpers():
    return dict(
        zip_tree=zip_tree
    )


def zip_tree(rsc):
    _list = _zip_list(rsc)

    if not _list:
        return None

    tree = OrderedDict()
    for compressed_file in _list:
        if "/" not in compressed_file.filename:
            data = {
                "title": compressed_file.filename,
                "file_size": (formatters.localised_filesize(
                              compressed_file.file_size)),
                "children": [],
                "icon": _get_icon(compressed_file.filename)
            }
            tree[compressed_file.filename] = data
        else:
            parts = compressed_file.filename.split("/")
            if parts[-1] != "":
                child = {
                    "title": re.sub(r"[^\x00-\x7f]", r"",
                                    parts.pop()),
                    "file_size": (formatters.localised_filesize(
                                  compressed_file.file_size)),
                    "children": [],
                    "icon": _get_icon(re.sub(r"[^\x00-\x7f]", r"",
                                      compressed_file.filename))
                }
                parent = "/".join(parts)
                if parent not in tree:
                    tree[parent] = {
                        "title": parent,
                        "children": [],
                        "icon": "folder-open"
                    }
                tree[parent]["children"].append(child)

    return tree.values()


def _get_icon(item):
    extension = item.split(".")[-1].lower()
    if extension in ["xml", "txt", "json"]:
        return "file-text"
    if extension in ["csv", "xls"]:
        return "bar-chart-o"
    if extension in ["shp", "geojson", "kml", "kmz"]:
        return "globe"
    return "file"


def _zip_list(rsc):
    if rsc.get("url_type") == "upload":
        upload = uploader.ResourceUpload(rsc)
        value = None
        try:
            zf = zipfile.ZipFile(upload.get_path(rsc["id"]), "r")
            value = zf.filelist
        except Exception as e:
            # Sometimes values that can"t be converted to ints can sneak
            # into the db. In this case, just leave them as they are.
            log.error("An error occured: {}".format(e))
        return value
    else:
        return _get_zip_list_from_url(rsc.get("url"))
    return None


def _get_zip_list_from_url(url):

    def get_list(start):
        headers = {"Range": "bytes={}-{}".format(start, end)}

        fp = StringIO(requests.get(url, headers=headers).content)
        zf = zipfile.ZipFile(fp)
        return zf.filelist

    try:
        head = requests.head(url)
        if "content-length" in head.headers:
            end = int(head.headers["content-length"])

        if "content-range" in head.headers:
            end = int(head.headers["content-range"].split("/")[1])

        return get_list(end - 65536)
    except Exception as e:
        log.error("An error occured: {}".format(e))
    try:
        return _get_list_advanced(url)
    except Exception as e:
        log.error("An error occured: {}".format(e))
        return None


def _open_remote_zip(url, offset=0):
    headers = {"Range": "bytes={}-".format(offset)}
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers))


def _get_list_advanced(url):
    # https://superuser.com/questions/981301/is-there-a-way-to-download-parts-of-the-content-of-a-zip-file


    offset = 0
    _list = []

    fp = _open_remote_zip(url)
    header = fp.read(30)

    while header[:4] == "PK\x03\x04":
        compressed_len, uncompressed_len = struct.unpack(
            "<II", header[18:26])
        filename_len, extra_len = struct.unpack("<HH", header[26:30])
        header_len = 30 + filename_len + extra_len
        total_len = header_len + compressed_len
        filename = fp.read(filename_len)

        zi = zipfile.ZipInfo(filename)
        zi.file_size = uncompressed_len
        _list.append(zi)
        fp.close()

        offset += total_len
        fp = _open_remote_zip(url, offset)
        header = fp.read(30)

    fp.close()
    return _list