#!/usr/bin/python
# -*- coding: utf-8 -*-

#    OpenDKIM genkeys tool
#    Copyright (C) 2018 Noel Kuntze <noel.kuntze+github@thermi.consulting>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import datetime
import glob
import importlib
import importlib.util
import logging
import os
import os.path
import shutil
import subprocess
import sys
import traceback
import yaml

class Genkeys():
    """ This class contains all methods of the opendkim-genkeys program """

    VERSION = "2.0.0"

    def __init__(self):
        self.args = None
        self.config = {
            "opendkim_dir" : "/etc/opendkim",
            "working_dir" : "",
            "update_dns" : True,
            "domain_file_name" : "domains.yml",
            "dns_api_defs_filename" : "dnsapi.yml",
            "dns_api_extra_data_file_name" : "dnsapi_extra.yml",
            "dns_update_data_file_name" : "dns_update_data.yml",
            "key_table" : "key.table",
            "signing_table" : "signing.table",
            "key_directory" : "/etc/opendkim/keys",
            "dnsapi_directory" : os.path.dirname(__file__),
            "cleanup_files" : True,
            "day_difference" : 70,
            "store_in_new_files" : False,
            "no_write_file" : False,
            "new_key_owner" : "opendkim",
            "new_key_group" : "root",
            "new_key_mode" : 0o400,
            "key_table_owner" : "root",
            "key_table_group" : "root",
            "key_table_mode" : 0o400,
            "signing_table_owner" : "root",
            "signing_table_group" : "root",
            "signing_table_mode" : 0o400
        }
        self.dns_api_data = {}
        self.domain_data = None
        self.logger = logging.getLogger(__file__)
        self.key_table_length = 0
        self.signing_table_length = 0
        self.dns_apis = {
            "null" : []
        }
        self.key_names = None
        self.key_data = None
        self.dns_api_extra = {}

    def read_config(self, config_path, config):
        """Reads the configuration from the given configuration path and sets the default
        configuration"""
        # Directory that OpenDKIM key files will be placed in on the mail server

        try:
            config.update(yaml.safe_load(open(config_path, "r")))
        except Exception as exception:
            logging.warning("Failed to load config from %s, resuming with defaults.", config_path)
        return config

    def read_dns_api(self, dns_api_data: str, dns_api_defs_filename: str, update_dns: bool):
        """Reads the dns API configuration file """
        # @returns Bool True if reading succeeded, False if it did not succeed.
        loaded_dns_api_data = {}
        try:
            # dns_api_data files are now yml files, not ini files
            loaded_dns_api_data = yaml.safe_load(open(dns_api_defs_filename, "r"))
            if not isinstance(loaded_dns_api_data, dict):
                self.logger.error(
                    "Incorrect file format in file %s, it needs to contain a dict. Aborting.",
                    dns_api_defs_filename)
                sys.exit(1)

        except Exception as exception:
            if not update_dns:
                logging.critical("Failed to load dns API definitions, aborting!")
                logging.critical("Exception: %s", exception)
                return False
        dns_api_data.update(loaded_dns_api_data)
        return True

    # @returns Bool True if reading succeeded, False if it did not succeed.
    def read_domain_data(self, domain_file_name):
        """Reads the domain data yaml file from domain_file_name """
        # api and parameters are stored in the file, which is a dictionary of the domains,
        # looks like this in Python {
        #   "example.com" : {
        #       "api" : "null",
        #       "parameters" : ["foo", "bar"]
        #       }
        #   }

        try:
            self.domain_data = yaml.safe_load(open(domain_file_name, "r"))
        except Exception as exception:
            logging.critical("Failed to load domain configuration, aborting!")
            logging.critical("Exception: %s", exception)
            return False

        logging.info("%s", self.domain_data)
        if self.domain_data is None:
            logging.critical("No domain definitions found.")
            return False
        # find any domains without configured api and set it to "null"
        for domain_data in self.domain_data.values():
            domain_data.setdefault("api", "null")
            domain_data.setdefault("parameters", [])

        return True

    def read_key_table(self, opendkim_dir: str, key_table: str):
        """ reads the key table (default is key.table) from the opendkim configuration directory
            @returns False or Dict of key name : {keyName, domain, selector, PathToKeyFile } """

        with open(opendkim_dir + "/" +  key_table, "r") as file:
            # the file contains nested structures as follows:
            # all entries
            #   key name
            #   domain
            #   selector
            #   path to keyfile

            # the dictionary holds the values in correspondingly named keys
            key_table_entries = {}
            for line in file.readlines():
                tokens = line.split()
                if len(tokens) == 2:
                    key_name = tokens[0]
                    colon_parts = tokens[1].split(":")
                    if len(colon_parts) == 3:
                        new_entry = {
                            "key_name" : tokens[0],
                            "domain" : colon_parts[0],
                            "selector" : colon_parts[1],
                            "path_to_keyfile" : colon_parts[2]
                            }
                        key_table_entries[key_name] = new_entry
                    else:
                        logging.warning(
                            "Encountered improperly formatted line discarding it: %s", line)
                else:
                    logging.warning("Encountered improperly formatted line discarding it: %s", line)
            return key_table_entries, len(key_table_entries)
        return False, False

    def read_dns_update_data(self, filename: str):
        """
        @input filename Path to yaml file to read
        @returns dict/list deserialised yaml object. The format is a list of objects with the
        following keys:
        domain_name, selector, creation_time, module_specific_information
        """
        file_contents = None
        try:
            file_contents = yaml.safe_load(open(filename, "r"))
        except Exception as exception:
            logging.warning("Failed to read DNS update data file. Resuming without it.")
            logging.warning("Exception: %s", exception)
            return []
        self.logger.debug("dns update data contents %s", file_contents)
        return file_contents

    def get_key_names(self):
        """ Get all key names from the key file """
        key_names = []
        for domain, domain_data in self.domain_data.items():
            key_name = domain_data.get("key")
            if key_name and key_name not in key_names:
                key_names.append(key_name)
            else:
                key_names.append(self.make_key_name(domain))
        return key_names

    def get_unknown_keys(self, known_keys, key_directory):
        """
        Retrieve the unknown keys in the key directory (its directory contents minus the known keys)
        """
        unknown_keys = []
        for file in os.listdir(key_directory):
            if file not in known_keys:
                unknown_keys.append(file)
        return unknown_keys

    @classmethod
    def generate_key_file_name(cls, key, selector):
        """
        Generate the file name of the private key for the given selector and domain key
        """
        return "{}.{}.key".format(key, selector)

    @classmethod
    def make_key_name(cls, name):
        """
        Generate the key name from the domain
        """
        return name.replace(".", "-")

    @classmethod
    def make_dkim_record_name(cls, selector: str, domain: str):
        """
        Generate the DNS record name for the selector and domain
        """
        return "%s._domainkey.%s" % (selector, domain)

    @classmethod
    def make_dkim_record_content(cls, public_key: str, version="DKIM1"):
        """
        Make the dkim record for the given pubkey and version in touple formatter
        """
        return [("v", version), ("h", "sha256"), ("k", "rsa"), ("s", "email"), ("p", public_key)]

    def generate_keys(self, selector: str, key_directory: str, key_names):
        """ Generate all keys """
        generated_key_data = {}
        for key in key_names:
            self.logger.info("Generating key %s", key)
            key_data = self.generate_singular_key(key, selector, key_directory)
            if key_data is None:
                logging.critical("Error generating key %s", key)
                return False
            generated_key_data[key] = key_data
        self.logger.debug("generated key data contents %s", generated_key_data)
        return generated_key_data

    def generate_singular_key(self, key, selector, key_directory, key_length=2048):
        """ generate the key pair using openssl rsa """

        new = False
        private_key_file_name = "{}/{}".format(
            key_directory,
            self.generate_key_file_name(
                key,
                selector))
        if not os.path.exists(private_key_file_name):
            self.logger.info("File %s for selector %s (key %s) does not exist yet, generating it.",
                             private_key_file_name, selector, key)
            # file does not exist
            process = subprocess.run(["openssl", "genrsa", "-out", private_key_file_name,
                                      str(key_length)], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            if process.returncode:
                self.logger.error(
                    "openssl genrsa failed with returncode %s and the following error output: %s",
                    process.returncode, process.stderr)
                return None
            # chown and chmod
            shutil.chown(
                private_key_file_name,
                user=self.config.get("new_key_owner"),
                group=self.config.get("new_key_group"))

            os.chmod(private_key_file_name, self.config["new_key_mode"])
            new = True
        else:
            logging.warning("Files for key %s selector %s already exist", key, selector)

        # convert to public key then generate TXT record, write and use it
        process = subprocess.run(["openssl", "rsa", "-in", private_key_file_name, "-pubout",
                                  "-outform", "PEM"], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)

        if process.returncode:
            self.logger.error("openssl rsa failed with returncode %s and the following error"
                              "output: %s", process.returncode, process.stderr)
            return None

        # public key is now in stdout, split by newline characters
        lines = process.stdout.decode("utf-8").split("\n")
        # strip first and last line (those are the PEM file format header and trailer)
        public_key_chunked = " ".join(lines[1:-2])
        # split every 250 characters
        return {
            "new" : new,
            "selector" : selector,
            "plain" : public_key_chunked.replace(" ", ""),
            "chunked" : public_key_chunked,
            "filename" : private_key_file_name
        }

    def test_dns_servers(self, dns_record_name: str, dns_record_content: str, domain: str):
        """Check if the given record name has the given content for the domain's configured DNS servers """
        ret = True
        servers = self.domain_data[domain].get("dns_servers")
        if servers:
            for server in servers:
                ret &= self.test_single_dns_server(dns_record_name, dns_record_content, server)
        return ret

    def test_single_dns_server(self, dns_record_name, dns_record_content, server):
        """ check if the given record can be resolved on the given server """
        try:
            proc = subprocess.run(
                ["dig", "+short", "TXT", dns_record_name, "@%s" % server],
                stdout=subprocess.PIPE)
            stdout = proc.stdout.decode("utf-8")
            self.logger.debug("Received from dig via stdout: %s", stdout)
            if not proc.returncode:
                self.logger.debug("Received from %s TXT value %s", server, stdout)
                # split by lines
                lines = stdout.splitlines()
                if len(lines) > 1:
                    self.logger.warning(
                        "There are %s records for the key. There must only be one!",
                        len(lines))
                    return False
                for line in lines:
                    self.logger.debug(line)
                    ret_inner = True
                    # basically join split strings
                    stdout = stdout.replace("\" \"", "").replace(";", "").replace("\"", "")
                    parameters = stdout.split(" ")
                    self.logger.debug("parameters: %s", parameters)
                    pairs = []
                    for token in parameters:
                        self.logger.debug(token)
                        tokens = token.split("=", maxsplit=2)
                        self.logger.debug(tokens)
                        token_1 = tokens[0]
                        token_2 = tokens[1]
                        pairs.append((token_1.replace("\n", ""), token_2.replace("\n", "")))
                    # sort provided and parsed lists
                    self.logger.debug("pairs: %s", pairs)
                    pairs.sort(key=lambda x: x[0], reverse=False)
                    dns_record_content.sort(key=lambda x: x[0], reverse=False)
                    for key_val_1, key_val_2 in zip(pairs, dns_record_content):
                        if key_val_1[0] != key_val_2[0] or key_val_1[1] != key_val_2[1]:
                            self.logger.error("Answer and provided content differ: %s != %s",
                                              key_val_1, key_val_2)
                            ret_inner = False
                            break
                    if ret_inner:
                        return True
            else:
                return False
        except Exception as exception:
            self.logger.error("An exception occured: %s", exception)
            self.logger.error("Exception info: %s", traceback.format_exc())
            return False
        return True

    def generate_selector(self):
        """Generate the selector for this month based upon the date"""
        selector_date = datetime.date.today().replace(day=1)
        if self.args.next_month:
            year = selector_date.year
            month = selector_date.month
            month += 1
            if month > 12:
                month = 1
                year += 1
            selector_date = selector_date.replace(year=year, month=month)
        return selector_date.strftime("%Y%m")

    def find_dns_api_modules(self):
        """Find all available DNS API modules (they're in the src directory)"""
        # Go through all possible names (pulled from what"s mentioned in the
        # dnsapi.yml file) and for each one X see if we can load a module named
        # dnsapi_X (file will be dnsapi_X.py).
        dns_apis = {}
        possible_names = self.dns_api_data.keys()
        should_update_dns = True

        for api_name in possible_names:
            module_name = "dnsapi_" + api_name
            try:
                spec = importlib.util.spec_from_file_location(
                    module_name, "%s/%s.py" % (self.config["dnsapi_directory"], module_name))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                sys.modules[module_name] = module
            except ImportError as exception:
                module = None
                self.logger.error("Module %s for DNS API %s not found", module_name, api_name)
                self.logger.info("%s", str(exception))
            if module is not None:
                self.logger.debug("DNS API module %s loaded", api_name)
                dns_apis[api_name] = module
        if not dns_apis:
            self.logger.warning("No DNS API modules found at %s", self.config["dnsapi_directory"])
            should_update_dns = False

        return dns_apis, should_update_dns

    def load_dns_api_module_extra_data(self, dns_api_extra_data_file_name):
        """
        Reads the dns_api_extra_data_file_name. It has to contain a dict
        indexed by the api names after which anything else can occur.
        """
        try:
            # dns_api_data files are now yml files, not ini files
            loaded_dns_api_extra = yaml.safe_load(
                open(dns_api_extra_data_file_name, "r"))
            if not isinstance(loaded_dns_api_extra, dict):
                self.logger.error(
                    "Incorrect file format in file %s, it needs to contain a dict. Aborting.",
                    "dns_api_extra_data_file_name")
                sys.exit(1)
            self.dns_api_extra.update(loaded_dns_api_extra)

        except Exception as exception:
            if not self.config["update_dns"]:
                self.logger.warning("Failed to load dns API extra data!")
                self.logger.warning("Exception: %s", exception)
        return True

    def save_dns_api_module_extra_data(self, dns_api_extra_data_file_name):
        return self.write_file(dns_api_extra_data_file_name, self.dns_api_extra)

    def initialize_dns_api_modules(self):
        for module_name, module in self.dns_apis.items():
            if hasattr(module, "init"):
                self.dns_api_extra[module_name] = module.init(self.dns_api_extra.get(module_name))

    def finish_dns_api_modules(self):
        for module_name, module in self.dns_apis.items():
            if hasattr(module, "finish"):
                module.finish(self.dns_api_extra.get(module_name))

    @classmethod
    def get_dns_update_data(cls, update_data, domain_name):
        ret = []
        for index, candidate in zip(range(0, len(update_data)), update_data):
            if candidate.get("domain") == domain_name:
                ret.append((index, candidate))
        return ret

    def cleanup_files(
            self,
            update_data: list,
            dns_domain_data: dict,
            key_data: dict,
            dns_api_module_name: str,
            day_difference: int):
        """ Remove old records from config files and remove old records from DNS"""
        removed_count = 0
        to_remove = []
        cutoff = datetime.datetime.today() - datetime.timedelta(day_difference)
        all_matching_records = self.get_dns_update_data(update_data, key_data["domain"])
        for index_and_record in  all_matching_records:
            date = index_and_record[1].get("creation_time")
            if date < cutoff:
                if removed_count == 0:
                    self.logger.info("Removing old records for %s", key_data["domain"])
                removed_count += 1
                result = self.dns_apis[dns_api_module_name].delete(
                    self.dns_api_data[dns_domain_data["api"]],
                    dns_domain_data, index_and_record[1],
                    self.dns_api_extra.get(dns_api_module_name),
                    self.args.log_debug)
                if result is None:
                    self.logger.info(
                        "No support for removing old record for %s:%s via %s API",
                        index_and_record[1]["domain"], index_and_record[1]["selector"],
                        dns_domain_data["api"])
                elif result:
                    # call returned True
                    self.logger.info(
                        "Removing %s:%s created at %s", index_and_record[1]["domain"],
                        index_and_record[1]["selector"], index_and_record[1]["creation_time"].strftime("%Y-%m-%d"))
                    to_remove.append(index_and_record[0])
                else:
                    # call returned False
                    self.logger.error(
                        "Error removing old record for %s:%s via %s API",
                        index_and_record[1]["domain"], index_and_record[1]["selector"],
                        dns_domain_data["api"])
                    # Preserve record if we encountered an error
        to_remove.sort(key=lambda x: x, reverse=True)
        for i in to_remove:
            update_data.pop(i)

    def write_file(self, file: str, data):
        """
        Write the data into file as yaml object using yaml.safe_dump, catch exceptions and log them
        """
        try:
            with open(file, "w") as handle:
                yaml.safe_dump(data, handle)
        except IOError as exception:
            self.logger.error("Failed to write to %s due to IO exception %s", file, exception)
        except Exception as exception:
            self.logger.error("Failed to write to %s due to general exception %s", file, exception)

    def update_domain(self, domain: str, failed_domains: list, update_data: list,
                      should_update_dns: bool):
        """
        Update the specified domain, cleanup outdated files
        """
        # work on every domain where an API with parameters is defined (have api and parameters)
        result = True
        domain_data = self.domain_data.get(domain)
        dns_apis = self.dns_apis
        if domain_data.get("api"):
            dns_api_name = domain_data["api"]
            dns_api_parameters = domain_data.get("parameters")
            dns_api_module = None
            # If the null API is to be used, set every domain's API to null or fail
            if self.args.use_null_dnsApi:
                if "fail" in self.dns_apis:
                    dns_api_module = dns_apis["fail"]
                else:
                    dns_api_module = dns_apis["null"]
            else:
                dns_api_module = dns_apis.get(dns_api_name)

            # if the API is available, apply the update
            if dns_api_module:
                self.logger.debug("Found DNS module %s for %s", dns_api_module, domain)
                dns_api_data = self.dns_api_data[dns_api_name]
                key_data = self.key_data[domain_data["key"]].copy()

                if dns_api_data and key_data:
                    key_data["domain"] = domain

                if self.config["cleanup_files"] and update_data is not None:
                    self.cleanup_files(update_data,
                                       domain_data, key_data, dns_api_name, 70)

                if should_update_dns:
                    dns_record_name = self.make_dkim_record_name(key_data["selector"], domain)
                    dns_record_content = self.make_dkim_record_content(key_data["plain"])
                    dns_record_exists = dns_api_module.check(
                        dns_api_data,
                        dns_api_parameters,
                        key_data,
                        self.dns_api_extra[dns_api_name],
                        self.args.log_debug)
                    # Add new record
                    # check if the record is available
                    # check if the DNS record exists at the provider
                    if not dns_record_exists:
                        self.logger.info("Adding selector %s for %s with key %s",
                                         key_data["selector"], domain, domain_data["key"])
                        result = dns_api_module.add(dns_api_data, dns_api_parameters, key_data,
                                                    self.dns_api_extra[dns_api_name],
                                                    self.args.log_debug)
                    record_available = self.test_dns_servers(
                        dns_record_name, dns_record_content, domain)
                    if not record_available:
                        self.logger.warning(
                            "Record %s is not available on its configured DNS servers. Skipping update.",
                            dns_record_name)
                        failed_domains.append(domain)
                    if result and record_available:
                        self.logger.info("Update succeeded.")
                        # remove old record
                        # only add if key is new
                        if key_data["new"]:
                            update_data.append({
                                "domain" : domain,
                                "selector" : key_data["selector"],
                                "creation_time" : datetime.datetime.today().strftime("%Y-%m-%d"),
                                "module_specific_information" : None
                            })
                    else:
                        self.logger.error("Failed to add a new record for %s with key %s via %s API",
                                          domain, domain_data["key"], dns_api_name)

                        failed_domains.append(domain)
            else:
                self.logger.error("Configured DNS API %s of %s not found!", dns_api_name,
                                  domain_data["api"])
                failed_domains.append(domain)

    def update_dns(
            self,
            should_update_dns: bool,
            dns_update_data_file_name: str,
            store_in_new_files: bool,
            cleanup_files: bool):
        """
        Update the DNS records
        """
        update_data = self.read_dns_update_data(dns_update_data_file_name)
        failed_domains = []
        if update_data is not None:
            # Convert update data timestamp field to a datetime
            for record in update_data:
                date = record.get("creation_time")
                if isinstance(date, str):
                    record["creation_time"] = datetime.datetime.strptime(date, "%Y-%m-%d")
        else:
            # create dns update data
            try:
                if store_in_new_files:
                    open(dns_update_data_file_name + ".new", "w")
                else:
                    open(dns_update_data_file_name, "w")
            except:
                self.logger.error("Failed to create %s", dns_update_data_file_name)
            update_data = []

        self.logger.info("Updating DNS records")
        # Discard records older than 10 weeks (roughly the midpoint of the month 2 months ago),
        # which should retain the last 2 records and discard the 3rd and older record if a monthly
        # rotation is in use.

        for domain in self.domain_data.keys():
            self.update_domain(domain, failed_domains, update_data, should_update_dns)

        self.write_file(dns_update_data_file_name, update_data)

        if cleanup_files:
            target_list = []
            # Find all files that match the name pattern for one of our
            # domain name abbreviations
            for target in self.key_names:
                target_list.extend(glob.glob("%s/keys/%s*.key" % (self.config["opendkim_dir"], target)))
            # Go through the update data and remove the entries from target_list that are
            # still referred to by an update_data item.
            for domain_update_data in update_data:
                print("domain_update_data: ", domain_update_data)
                # if there are insufficient parameters in the object, it is skipped.
                # It needs to have at least a domain name and a selector
                if len(domain_update_data) < 2:
                    self.logger.debug("Skipping domain because of too few parameters")
                    continue

                domain_key = self.domain_data.get(domain_update_data["domain"])
                print("domain_key: ", domain_key)
                if domain_key is not None:
                    for suffix in [".key", ".txt"]:
                        item_str = domain_key["key"] + "." + domain_update_data["selector"] + suffix
                        print("item_str: ", item_str)
                        try:
                            i = target_list.index(item_str)
                        except ValueError:
                            i = -1
                        if i >= 0:
                            target_list.pop(i)
            # Don't clean entries for domains that failed the DNS update
            for failed_domain in failed_domains:
                domain_key_str = self.domain_data.get(failed_domain)["key"]
                print(domain_key_str)
                if domain_key_str:
                    new_list = [x for x in target_list if not x.startswith(domain_key_str + ".")]
                    target_list = new_list
            # What's left in target_list are just the files that aren't referred to anymore and
            # are eligible for being deleted.
            for filename in target_list:
                self.logger.info("Removing obsolete file %s", filename)
                try:
                    # os.remove(filename)
                    pass
                except:
                    logging.warning("Failed to remove obsolete file %s", filename)
        return failed_domains

    def write_tables(self, key_domain_table, selector, failed_domains, store_in_new_files, key_directory):
        """
        Write the domain data and key domain table into key.table and signing.table in the
        format opendkim expects
        """

        key_table_file = None
        key_table_file_name = "key.table"
        signing_table_file = None
        signing_table_file_name = "signing.table"

        if store_in_new_files:
            key_table_file_name += ".new"
            signing_table_file_name += ".new"

        try:
            key_table_file = open(key_table_file_name, "w")
            signing_table_file = open(signing_table_file_name, "w")
        except IOError as exception:
            logging.critical("Error creating new key or signing table file")
            self.logger.error("%s", str(exception))
            sys.exit(1)
        # Write the unupdated entries back to the files
        for key_domain_data in key_domain_table.values():
            if key_domain_data["domain"] in failed_domains:
                self.logger.info("Preserving entries for %s", key_domain_data["key_name"])
                try:
                    key_table_file.write(
                        "%s\t%s:%s:%s\n" % (key_domain_data["key_name"], key_domain_data["domain"],
                                            key_domain_data["selector"],
                                            key_domain_data["path_to_keyfile"]))
                    signing_table_file.write("*@%s\t%s\n" % (key_domain_data["domain"],
                                                             key_domain_data["key_name"]))
                except IOError as exception:
                    logging.critical("Error writing new key or signing table file")
                    self.logger.error("%s", str(exception))
                    return False
        # Now write the updated lines to the files
        for domain, domain_data in self.domain_data.items():
            if domain not in failed_domains:
                self.logger.info("Adding entries for %s", domain)
                try:
                    key_table_file.write("%s\t%s:%s:%s/%s.%s.key\n" % \
                                          (domain_data["key"], domain, selector, key_directory,
                                           domain_data["key"], selector))
                    signing_table_file.write("*@%s\t%s\n" % (domain, domain_data["key"]))
                except IOError as exception:
                    logging.critical("Error writing new key or signing table file")
                    self.logger.error("%s", str(exception))
                    return False
        key_table_file.close()
        signing_table_file.close()
        # change owner and group
        shutil.chown(
            key_table_file_name,
            user=self.config.get("key_table_owner"),
            group=self.config.get("key_table_group"))
        shutil.chown(
            signing_table_file_name,
            user=self.config.get("signing_table_owner"),
            group=self.config.get("signing_table_group"))

        os.chmod(key_table_file_name, self.config["key_table_mode"])
        os.chmod(signing_table_file_name, self.config["signing_table_mode"])
        return True

    def parse_args(self):
        """
        Set up command-line argument parser and parse arguments
        """
        parser = argparse.ArgumentParser(description="Generate OpenDKIM key data for a set of"
                                         " domains")
        parser.add_argument("-v", "--verbose", dest="log_info", action="store_true",
                            help="Log informational messages in addition to errors")
        parser.add_argument("-n", "--next-month", dest="next_month", action="store_true",
                            help="Use next month's date for automatically-generated selectors")
        parser.add_argument("-s", "--selector", dest="output_selector", action="store_true",
                            help="Causes the generated selector to be output")
        parser.add_argument("--working-dir", dest="working_dir", action="store",
                            help="Set the working directory for DKIM data files",
                            default=argparse.SUPPRESS)
        parser.add_argument("--opendkim-dir", dest="opendkim_dir", action="store",
                            help="The directory of the opendkim configuration",
                            default="/etc/opendkim")
        parser.add_argument("--key-directory", dest="key_directory", action="store",
                            help="The directory of the opendkim keys directory",
                            default="/etc/opendkim/keys")
        parser.add_argument("--dnsapi-directory", dest="dnsapi_directory", action="store",
                            help="The directory in which the dnsapi modules are stored",
                            default=os.path.dirname(__file__))
        parser.add_argument("--config", action="store",
                            help="The path to the configuration file",
                            default="/etc/opendkim-genkeys.yml")
        parser.add_argument("--no-dns", dest="no_update_dns", action="store_false",
                            default=argparse.SUPPRESS,
                            help="Do not update DNS data")
        parser.add_argument("--no-cleanup", dest="no_cleanup_files", action="store_false",
                            default=argparse.SUPPRESS,
                            help="Do not delete old key files")
        parser.add_argument("--debug", dest="log_debug", action="store_true",
                            help="Log debugging info")
        parser.add_argument("--use-null", dest="use_null_dnsApi", action="store_true",
                            help="Silently use the null DNS API instead of the real API")
        parser.add_argument("--no-write-file", dest="no_write_file", action="store_true",
                            default=argparse.SUPPRESS,
                            help="Disable writing any file changes to the key or signing table, or any of the yml files.")
        parser.add_argument("--store-in-new-files", dest="store_in_new_files", action="store_true",
                            default=argparse.SUPPRESS,
                            help="Do not overwrite old key and signing table files or dns_update_data.yml files, but write new ones")
        parser.add_argument("--version", dest="display_version", action="store_true",
                            help="Display the program version")
        parser.add_argument("selector", nargs="?", default=None, help="Selector to use")
        parser.add_argument("domains", nargs=argparse.REMAINDER, help="List of domains to process")

        self.args = parser.parse_args()

        if self.args.display_version:
            print("OpenDKIM genkeys %s" % self.VERSION)
            sys.exit(0)

    def overwrite_from_args(self):
        """
        Handle overwriting config file values from passed arguments
        """
        if hasattr(self.args, "no_update_dns"):
            self.logger.debug("Overwriting updating to dns from args: %s", self.args.update_dns)
            self.config["should_update_dns"] = self.args.no_update_dns

        if hasattr(self.args, "no_cleanup_files"):
            self.logger.debug("Overwriting cleaning up old key files from args: %s", self.args.cleanup_files)
            self.config["cleanup_files"] = self.args.no_cleanup_files

        if hasattr(self.args, "no_write_file"):
            self.logger.debug("Overwriting cleaning up old key files from args: %s", self.args.no_write_file)
            self.config["no_write_file"] = self.args.no_write_file

        if hasattr(self.args, "store_in_new_files"):
            self.logger.debug("Overwriting store_in_new_files from args: %s", self.args.store_in_new_files)
            self.config["store_in_new_files"] = self.args.store_in_new_files
        if hasattr(self.args, "working_dir"):
            self.logger.debug("Setting working directory from argument: %s", self.args.working_dir)
            os.chdir(self.args.working_dir)
        else:
            config_wd = self.config.get("working_dir")
            if config_wd and config_wd != "":
                self.logger.debug("Setting working directory from config: %s", config_wd)
                os.chdir(config_wd)
        self.config["dnsapi_directory"] = self.args.dnsapi_directory

    def decide_arguments(self):
        """
        Decide on values of internal configuration
        """
        should_update_dns = self.config["update_dns"]

        level = logging.WARN
        if self.args.log_debug:
            level = logging.DEBUG
        elif self.args.log_info:
            level = logging.INFO

        if self.args.output_selector:
            should_update_dns = False
            level = logging.ERROR
        self.logger.setLevel(level)
        logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
        if self.args.output_selector:
            self.logger.debug("Disabling updating DNS because outputting a selector is enabled")

        selector = self.args.selector
        if selector is None:
            selector = self.generate_selector()
        else:
            self.logger.info("Selector: %s", selector)
            if self.args.output_selector:

                sys.exit(0)

        return should_update_dns, selector

    def read_files(
            self,
            dns_api_data,
            dns_api_extra_data_file_name,
            dns_api_defs_filename,
            update_dns,
            domain_file_name):
        """
        Read dnsapi.yml, dnsapi_extra.yml and domains.yml files.
        """
        self.logger.debug("Reading files")
        self.read_dns_api(dns_api_data, dns_api_defs_filename, update_dns)
        self.load_dns_api_module_extra_data(dns_api_extra_data_file_name)

        if not self.read_domain_data(domain_file_name):
            sys.exit(1)

    def main(self):
        """
        main function
        """

        self.parse_args()

        self.read_config(self.args.config, self.config)

        should_update_dns, selector = self.decide_arguments()

        self.overwrite_from_args()

        self.read_files(
            self.dns_api_data,
            self.config["dns_api_extra_data_file_name"],
            self.config["dns_api_defs_filename"],
            self.config["update_dns"],
            self.config["domain_file_name"]
            )
        self.key_names = self.get_key_names()

        self.key_data = self.generate_keys(selector, self.config["key_directory"], self.key_names)

        key_table_contents, self.key_table_length = self.read_key_table(
            self.config["opendkim_dir"],
            self.config["key_table"]
            )

        if not key_table_contents:
            key_table_contents = {}


        # Check for our DNS API modules. If we don"t have any, there"s no sense in
        # trying to do automatic updating even if we"re supposed to.
        self.dns_apis, should_update_dns_new = self.find_dns_api_modules()
        should_update_dns = should_update_dns and should_update_dns_new

        self.initialize_dns_api_modules()
        failed_domains = self.update_dns(
            should_update_dns,
            self.config["dns_update_data_file_name"],
            self.config["store_in_new_files"],
            self.config["cleanup_files"])

        self.finish_dns_api_modules()
        if not self.config["no_write_file"] and self.key_table_length == len(key_table_contents):
            self.logger.info("Generating key and signing tables")
            self.write_tables(
                key_table_contents,
                selector,
                failed_domains,
                self.config["store_in_new_files"],
                self.config["key_directory"])
        else:
            self.logger.info("Not writing key or signing tables")

        self.save_dns_api_module_extra_data(self.config["dns_api_extra_data_file_name"])

        sys.exit(0)

if __name__ == "__main__":
    GENKEYS = Genkeys()
    GENKEYS.main()
