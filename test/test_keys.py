import os
import pytest
import subprocess
import sys

sys.path.append("%s/../src" % os.path.dirname(__file__))

import genkeys

def test_get_unknown_keys():
    pass

def test_generate_key_file_name():
    genkeys_module = genkeys.Genkeys()
    assert genkeys_module.generate_key_file_name("foo", "bar") == "foo.bar.key"

def test_make_key_name():
    genkeys_module = genkeys.Genkeys()
    assert genkeys_module.make_key_name("example.com") == "example-com"

def test_make_dkim_record_name():
    genkeys_module = genkeys.Genkeys()
    generated_record_name = genkeys_module.make_dkim_record_name("test_selector", "example.com")
    valid_test_record_name = "test_selector._domainkey.example.com"
    assert generated_record_name == valid_test_record_name

def test_make_dkim_record_content():
    genkeys_module = genkeys.Genkeys()
    test_publickey = "test_abc"
    valid_dkim_record_content = [("v", "DKIM1"), ("h", "sha256"), ("k", "rsa"), ("s", "email"), ("p", test_publickey)]
    generated_dkim_record_content = genkeys_module.make_dkim_record_content(test_publickey)
    assert valid_dkim_record_content == generated_dkim_record_content

def test_generate_keys(tmpdir):
    class FakeArg():
        next_month = False
    genkeys_module = genkeys.Genkeys()
    genkeys_module.args = FakeArg()
    selector = genkeys_module.generate_selector()
    # predefined private_keys
    test_keys = {
        "test_1" : {
            "new" : False,
            "selector" : selector,
            "private_key" : """\
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtSM6zxmpP5c/uoM7JZPHhYwerwXAcvNHsX/lDAOIYmMHrSzK
/VWmH2L7wMd0XXNpT+iHxf3GPzHSXp21PpofVYSeQHVyjGAnXnrHjat3OExL+RYw
F4INaETRePr5c9sWYIGv5vLwiePHV4fZJr6QnNhtPWxWRp14ZVn8eO+DFjIz+l+g
SGsfxH0xntcrXtNVmA3D0r7l8grMkd8k/Zf0v3qTMJYIEom1OzDWaTB7zoLKof3U
IPskXLspTmTpIEY3+9507BjMBpBO08gWgnfF97M4F0mseyUkCJmZZMyVKnPAHAkY
X90aoANPXUYJ8qoBPjT3I5yT92yEwtKIQn4NxwIDAQABAoIBAHjgV6BYiX8sGZUH
efLrmRvfk6JMfk63VkJ3DIxl1x+A4mCIIbXI8CDF1yagc2DhYYe3rtNLNH57at1E
9OwfwYU6CLkPJy/SArOjz4MUx2xETfac/d7SJMxOEFNheBH+RAKGyLGfsTDzVdVt
jFW0maBxNQTmRPS+pNdNo5O4kYu/OLgB5FyDCNAwT0LB9PIvIHI4Wct9mzHdVIyf
NaLsIYd2DX0rbERNYtCcoTQgGBolxMCPmZu7xYurjAwRNY18NQ6NVw7oInCMOXib
i2epiLPgy2LK956Bafo9i3Rp3sesblW6IHhaKaXCcP69As6Cu9izIAzQNkWUv2OT
CUjAY5ECgYEA5d8IKNGFZgaIX++ZVje/r7mBicBEb0iKuHpedSPB2QxYeaoMziBn
aKRqt2XFOCpcZrF71rCHXkwSRoq1szmsAq588WKsy7h4bjq7qW3E5Y3/DdxN47fg
azP1d5COpjsvHJ1PHao87VYj01oByAm7noOA6i6fF8xdZlfM8lZd8i0CgYEAyboc
PPMmFWnYfbP2zqGFcwdvpk48MHIfWgfRCBA9pLvzfO92N54jJbKm4Dk6p6RlhY96
GTBn9yUJEsQTOhOAKxnVAcv+TyMNzyA8k9YMYCQnlAe9RATDiufR+qVA4GWkxBM3
lYWZbAEQ1lmPVodp1dlS0YUse5uDCYfXoU2N3EMCgYEAm3WkrQZV81QDsu31g6uc
RZltk92l6qTivDR14T7XgJSq2U0578VWahyX14RKRtvPNdxeZilow0srKO3ySE1+
mSmscgtL1VLij5nFBKap/J11msgdHR5j9dxj7AKllqJ8EBwLP4K8Rb516B/9CG4c
pu1EqBvzmEKr/+TtRA9I5dkCgYA9aduO8rd1bXPrUQ6ieaoXCvyCtO6+EQBaeGa6
/bbGoDHQp1ZmOE6a+3iyarngr7v4nWWepY4BP9UzUV5JIAa1GHgww9n4XcOmezn2
CARcgKVL+88zFgAyGcFjfUvzBP7UcsVJUBMVPn3RxBJPVYpzAGamQtT4DLAoBqMv
CF1X4QKBgHJwcHFTabhfYn2NZ4vGOjs4kY5J4nyE3kef6leyjE9i1rhvMJ547gQm
Y+XB0wES9JgkdkAtsS2kb7cOJE+fDkd+imSn7a5cDlcr32G/9jLz1dlk22Vs1reu
o2Wp4EN0+2u1qFUGsfTlefLixjY8KpHKetPDtXK5xYiMPPDRDImP
-----END RSA PRIVATE KEY-----""",
            "plain" : "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC"\
            "AQEAtSM6zxmpP5c/uoM7JZPHhYwerwXAcvNHsX/lDAOIYmMHr"\
            "SzK/VWmH2L7wMd0XXNpT+iHxf3GPzHSXp21PpofVYSeQHVyjG"\
            "AnXnrHjat3OExL+RYwF4INaETRePr5c9sWYIGv5vLwiePHV4fZ"\
            "Jr6QnNhtPWxWRp14ZVn8eO+DFjIz+l+gSGsfxH0xntcrXtNVm"\
            "A3D0r7l8grMkd8k/Zf0v3qTMJYIEom1OzDWaTB7zoLKof3UIP"\
            "skXLspTmTpIEY3+9507BjMBpBO08gWgnfF97M4F0mseyUkCJm"\
            "ZZMyVKnPAHAkYX90aoANPXUYJ8qoBPjT3I5yT92yEwtKIQn4NxwIDAQAB",
            "chunked" : "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC"\
            "AQEAtSM6zxmpP5c/uoM7JZPH hYwerwXAcvNHsX/lDAOIYmMHr"\
            "SzK/VWmH2L7wMd0XXNpT+iHxf3GPzHSXp21Ppof VYSeQHVyjG"\
            "AnXnrHjat3OExL+RYwF4INaETRePr5c9sWYIGv5vLwiePHV4fZ"\
            "Jr6Q nNhtPWxWRp14ZVn8eO+DFjIz+l+gSGsfxH0xntcrXtNVm"\
            "A3D0r7l8grMkd8k/Zf0 v3qTMJYIEom1OzDWaTB7zoLKof3UIP"\
            "skXLspTmTpIEY3+9507BjMBpBO08gWgnfF 97M4F0mseyUkCJm"\
            "ZZMyVKnPAHAkYX90aoANPXUYJ8qoBPjT3I5yT92yEwtKIQn4N xwIDAQAB",
            "filename" : "%s/test_1.%s.key" % (tmpdir, selector)
        }
    }



    key_names = [
        "test_2"
    ]
    # write private keys
    os.chdir(tmpdir)

    for key_name, key_data in test_keys.items():
        key_names.append(key_name)
        path = "%s" % key_data["filename"]
        with open(path, "w") as file:
            file.write(key_data["private_key"])

    genkeys_module.config["new_key_owner"] = os.getuid()
    genkeys_module.config["new_key_group"] = os.getgid()
    generated_key_data = genkeys_module.generate_keys(selector, tmpdir, key_names)
    # check if all generated files exist and if they are valid keys
    if not:
        genkeys_module.error("Failed to generate keys.")
        sys.exit(1)

    found = []
    for key_name, key_data in generated_key_data.items():
        # iterate over selector and key data
        predefined = test_keys.get(key_name)
        assert isinstance(key_data, dict)
        assert isinstance(key_data["new"], bool)
        file_name = key_data.get("filename")
        assert os.path.exists(file_name)
        #key_contents = open(file_name, "r", encoding="utf-8").read()

        if predefined:
            assert predefined["selector"] == selector
            assert not key_data["new"], "Key %s is declared as new but is old!" % key_name
            assert key_data.get("selector") == predefined["selector"]
            assert key_data.get("selector") == selector
            assert key_data["new"] == predefined["new"]
            # get pubkey
            print(key_data["plain"])
            print(predefined["plain"])
            assert key_data["plain"] == predefined["plain"]
            assert key_data["chunked"] == predefined["chunked"]
        else:
            assert key_data["new"]


        found.append(key_name)
        # check if selector and key_data are predefined
        # check if they're equal
        # add to found

    # check if key_names == found
    for item in key_names:
        assert item in found

def test_write_tables(tmpdir):
    failed_domains = []
    store_in_new_files = False
    key_directory = tmpdir
    known_good_key_table_content = """\
test_1\texample_1.com:2000-01-01:%s/test_1.2000-01-01.key
test_2\texample_2.com:2000-01-01:%s/test_2.2000-01-01.key
""" % (tmpdir, tmpdir)
    known_good_signing_table_content = """\
*@example_1.com\ttest_1
*@example_2.com\ttest_2
"""
    genkeys_module = genkeys.Genkeys()
    genkeys_module.domain_data = {
        "example_1.com" : {
            "key" : "test_1"
        },
        "example_2.com" : {
            "key" : "test_2"
        }
    }
    genkeys_module.config.update(
        {
            "key_table_owner" : os.getuid(),
            "key_table_group" : os.getgid(),
            "signing_table_owner" : os.getuid(),
            "signing_table_group" : os.getgid()
        })
    selector = "2000-01-01"
    key_table_name = "key.table"
    signing_table_name = "signing.table"
    test_key_domain_table = {
        1 : {
            "domain" : "example_1.com",
            "key_name" : "test_1",
            "selector" : selector,
            "path_to_keyfile" : "test_123.key"
        },
        2 : {
            "domain" : "example_2.com",
            "key_name" : "test_2",
            "selector" : selector,
            "path_to_keyfile" : "test_456.key"
        }
    }
    os.chdir(tmpdir)
    assert genkeys_module.write_tables(
        test_key_domain_table,
        selector,
        failed_domains,
        store_in_new_files,
        key_directory)
    assert os.path.exists("key.table")
    assert os.path.exists("signing.table")
    key_table_content = open(key_table_name, "r", encoding="utf-8").read()
    signing_table_content = open(signing_table_name, "r", encoding="utf-8").read()
    assert key_table_content == known_good_key_table_content
    assert signing_table_content == known_good_signing_table_content

def test_generate_singular_key():
    pass

def test_test_dns_servers():
    pass

def test_test_single_dns_server():
    pass

def test_generate_selector():
    pass

def test_find_dns_api_modules(tmpdir):
    src_path = "%s/../src" % os.path.dirname(__file__)
    print(__file__)
    genkeys_module = genkeys.Genkeys()
    genkeys_module.config.update({"opendkim_dir" : src_path, "dnsapi_directory" : src_path})
    genkeys_module.dns_api_data = {
        "null": [],
        "freedns" : [
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        ],
        "linode" : [
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        ],
        "route53" :[
            "xxxxxxxxxxxxxxxxxxxx",
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        ],
        "cloudflare" : [
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "user@domain.com"
        ],
        "cloudflareapi" : [
            "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "user@domain.com"
        ]
    }
    to_find = ["null", "freedns", "linode", "route53", "cloudflare", "cloudeflareapi"]
    print(src_path)
    os.chdir(tmpdir)
    print(os.listdir(src_path))
    modules, should_update_dns = genkeys_module.find_dns_api_modules()
    print(modules)
    assert should_update_dns
    found = []
    for module in modules:
        assert module in to_find
        found.append(module)
    assert to_find.sort() == found.sort()

def test_load_dns_api_module_extra_data():
    pass
