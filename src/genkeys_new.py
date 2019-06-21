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
import logging
import os
import os.path
import string
import subprocess
import sys
import yaml

class Genkeys():
    """ This class contains all methods of the opendkim-genkeys program """

    VERSION = "2.0.0"

    def __init__(self):
        self.args = None
        self.config = None
        self.dns_api_data = {}
        self.domain_data = None
        self.logger = logging.getLogger(__name__)
        self.key_table_length = 0
        self.signing_table_length = 0
        self.dns_apis = {
            "null" : []
        }
        self.key_names = None
        self.key_data = None
        self.dns_api_extra = {}

    def read_config(self, config_path):
        """Reads the configuration from the given configuration path and sets the default
        configuration"""
        # Directory that OpenDKIM key files will be placed in on the mail server
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
            "cleanup_files" : True,
            "day_difference" : 70,
            "store_in_new_files" : False,
            "no_write_file" : False
        }

        try:
            self.config.update(yaml.safe_load(open(config_path, "r")))
        except Exception as exception:
            logging.warning("Failed to load config from %s, resuming with defaults.", config_path)

    def read_dns_api(self):
        """Reads the dns API configuration file """
        # @returns Bool True if reading succeeded, False if it did not succeed.
        loaded_dns_api_data = {}
        try:
            # dns_api_data files are now yml files, not ini files
            loaded_dns_api_data = yaml.safe_load(open(self.config["dns_api_defs_filename"], "r"))
            if not isinstance(loaded_dns_api_data, dict):
                self.logger.error(
                    "Incorrect file format in file %s, it needs to contain a dict. Aborting.",
                    self.config["dns_api_defs_filename"])
                sys.exit(1)

        except Exception as exception:
            if not self.config["update_dns"]:
                logging.critical("Failed to load dns API definitions, aborting!")
                logging.critical("Exception: %s", exception)
                return False
        self.dns_api_data.update(loaded_dns_api_data)
        return True

    # @returns Bool True if reading succeeded, False if it did not succeed.
    def read_domain_data(self):
        """Reads the domain data yaml file from self.config["domain_file_name"] """
        # api and parameters are stored in the file, which is a dictionary of the domains,
        # looks like this in Python {
        #   "example.com" : {
        #       "api" : "null",
        #       "parameters" : ["foo", "bar"]
        #       }
        #   }

        try:
            self.domain_data = yaml.safe_load(open(self.config["domain_file_name"], "r"))
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

    def read_key_table(self):
        """ reads the key table (default is key.table) from the opendkim configuration directory
            @returns False or Dict of key name : {keyName, domain, selector, PathToKeyFile } """

        with open(self.config["opendkim_dir"] + "/" +  self.config["key_table"], "r") as file:
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

            self.key_table_length = len(key_table_entries)
            return key_table_entries
        return False

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
        for domain_data in self.domain_data.values():
            key_name = domain_data.get("key")
            if key_name is not None and key_name not in key_names:
                key_names.append(key_name)
        return key_names

    @classmethod
    def make_dkim_record_name(cls, selector: str, domain:str):
        """
        Generate the DNS record name for the selector and domain
        """
        return "%s._domainkey.%s" % (selector, domain)

    @classmethod
    def make_dkim_record_content(cls, public_key: str, version="DKIM1"):
        return [ ("v", version), ("h", "sha256"), ("k", "rsa"), ("s", "email"), ("p", public_key) ]

    def generate_keys(self, selector: str):
        """ Generate all keys """
        generated_key_data = {}
        for key in self.key_names:
            self.logger.info("Generating key %s", key)
            key_data = self.generate_singular_key(key, selector)
            if key_data is None:
                logging.critical("Error generating key %s", key)
                return False
            generated_key_data[key] = key_data
        self.logger.debug("generated key data contents %s", generated_key_data)
        return generated_key_data

    def generate_singular_key(self, key, selector, key_kength=2048):
        """ generate the key pair using openssl rsa """

        new = False
        private_key_file_name = "{}/{}.{}.key".format(self.config["key_directory"], key,
                                                      selector)
        if not os.path.exists(private_key_file_name):
            self.logger.info("File %s for selector %s (key %s) does not exist yet, generating it.",
                             private_key_file_name, key, selector)
            # file does not exist
            process = subprocess.run(["openssl", "genrsa", "-out", private_key_file_name, "--",
                                      str(key_kength)], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            if process.returncode:
                self.logger.error(
                    "openssl genrsa failed with returncode %s and the following error output: %s",
                    process.returncode, process.stderr)
                return None
            else:
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
            "chunked" : public_key_chunked
        }

    def test_dns_servers(self, dns_record_name: str, dns_record_content: str, domain: str, domain_key: str):
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
                logging.debug("Received from %s TXT value %s", server, stdout)
                # basically join split strings
                stdout = stdout.replace("\" \"", "")
                stdout = stdout.replace(";", "")
                stdout = stdout.replace("\"", "")
                print(stdout)
                parameters = stdout.split(" ")
                print(parameters)
                last = None
                pairs = []
                i = 0
                for token in parameters:
                    t1, t2 = token.split("=")
                    pairs.append((t1.replace("\n", ""), t2.replace("\n", "")))

                # sort provided and parsed lists
                pairs.sort(key=lambda x: x[0], reverse=False)
                dns_record_content.sort(key=lambda x: x[0], reverse=False)
                for key_val_1, key_val_2 in zip(pairs, dns_record_content):
                    if key_val_1[0] != key_val_2[0] or key_val_1[1] != key_val_2[1]:
                        logging.error("Answer and provided content differ: %s != %s", key_val_1, key_val_2)
                        return False
                return True
            else:
                return False
        except Exception as exception:
            logging.error("An exception occured: %s", exception)
            return False

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
        """Find all available DNS API modules (they're in the src directory"""
        # Go through all possible names (pulled from what"s mentioned in the
        # dnsapi.yml file) and for each one X see if we can load a module named
        # dnsapi_X (file will be dnsapi_X.py).
        dns_apis = {}
        possible_names = self.dns_api_data.keys()
        should_update_dns = True

        for api_name in possible_names:
            module_name = "dnsapi_" + api_name
            try:
                module = importlib.import_module(module_name)
            except ImportError as exception:
                module = None
                self.logger.error("Module %s for DNS API %s not found", module_name, api_name)
                self.logger.info("%s", str(exception))
            if module is not None:
                self.logger.debug("DNS API module %s loaded", api_name)
                dns_apis[api_name] = module
        if not dns_apis:
            logging.warning("No DNS API modules found at %s", os.path.dirname(__file__))
            should_update_dns = False

        return dns_apis, should_update_dns

    def load_dns_api_module_extra_data(self):
        """
        Reads the dns_api_extra_data_file_name. It has to contain a dict indexed by the api names after
        which anything else can occur.
        """
        try:
            # dns_api_data files are now yml files, not ini files
            loaded_dns_api_extra = yaml.safe_load(open(self.config["dns_api_extra_data_file_name"], "r"))
            if not isinstance(loaded_dns_api_extra, dict):
                self.logger.error(
                    "Incorrect file format in file %s, it needs to contain a dict. Aborting.",
                    self.config["dns_api_extra_data_file_name"])
                sys.exit(1)
            self.dns_api_extra.update(loaded_dns_api_extra)

        except Exception as exception:
            if not self.config["update_dns"]:
                logging.warning("Failed to load dns API extra data!")
                logging.warning("Exception: %s", exception)
        return True

    def save_dns_api_module_extra_data(self):
        return self.write_file(self.config["dns_api_extra_data_file_name"], self.dns_api_extra)

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
            if candidate.get("domain_name") == domain_name:
                ret.append((index, candidate))
        return ret

    def cleanup_files(self, update_data: list, dns_domain_data: dict, key_data: dict,
        dns_api_module_name: str, day_difference: int):
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
                    self.dns_api_data[dns_domain_data["api"]]["parameters"],
                    dns_domain_data, all_matching_records[1],
                    self.dns_api_extra.get(dns_api_module_name),
                    self.args.log_debug)
                if result is None:
                    self.logger.info(
                        "No support for removing old record for %s:%s via %s API",
                        all_matching_records[1]["domain"], all_matching_records[1]["key"],
                        dns_domain_data["api"])
                elif result:
                    # call returned True
                    self.logger.info(
                        "Removing %s:%s created at %s", all_matching_records[1]["domain"],
                        all_matching_records[1]["key"], index_and_record[1]["date"].strftime("%Y-%m-%d"))
                    to_remove.append(all_matching_records[0])
                else:
                    # call returned False
                    self.logger.error(
                        "Error removing old record for %s:%s via %s API",
                        all_matching_records[1]["domain"], all_matching_records[1]["key"],
                        dns_domain_data["api"])
                    # Preserve record if we encountered an error
        print(update_data)
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
                print(key_data)

                if self.config["cleanup_files"] and update_data is not None:
                    self.cleanup_files(update_data,
                                       domain_data, key_data, dns_api_module, 70)

                if should_update_dns:
                    dns_record_name = self.make_dkim_record_name(key_data["selector"], domain)
                    dns_record_content = self.make_dkim_record_content(key_data["plain"])
                    # Add new record
                    self.logger.info("Updating selector %s for %s with key %s",
                                     key_data["selector"], domain, domain_data["key"])
                    result = dns_api_module.add(dns_api_data, dns_api_parameters, key_data,
                                                self.dns_api_extra[dns_api_name],
                                                self.args.log_debug)
                    record_available = self.test_dns_servers(
                        dns_record_name, dns_record_content, domain, domain_data["key"])

                    if not record_available:
                        logging.warning(
                            "Record %s is not available on its configured DNS servers. Skipping update.",
                            dns_record_name
                            )
                    if result[0] and record_available:
                        self.logger.info("Update succeeded.")
                        # remove old record
                        # only add if key is new
                        if key_data["new"]:
                            update_data.append({
                                "domain_name" : domain,
                                "selector" : key_data["selector"],
                                "creation_time" : datetime.datetime.today().strftime("%Y-%m-%d"),
                                "module_specific_information" : None
                            })
                        print(update_data)
                    else:
                        self.logger.error("Error adding new record for %s with key %s via %s API",
                                          domain, domain_data["key"], dns_api_name)

                        failed_domains.append(domain)
            else:
                self.logger.error("Configured DNS API %s of %s not found!", dns_api_name,
                                  domain_data["api"])
                failed_domains.append(domain)

    def update_dns(self, should_update_dns: bool):
        update_data = self.read_dns_update_data(self.config["dns_update_data_file_name"])
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
                if self.config["store_in_new_files"]:
                    open(self.config["dns_update_data_file_name"] + ".new", "w")
                else:
                    open(self.config["dns_update_data_file_name"], "w")
            except:
                self.logger.error("Failed to create %s", self.config["dns_update_data_file_name"])
            update_data = []

        self.logger.info("Updating DNS records")
        # Discard records older than 10 weeks (roughly the midpoint of the month 2 months ago),
        # which should retain the last 2 records and discard the 3rd and older record if a monthly
        # rotation is in use.

        for domain in self.domain_data.keys():
            self.update_domain(domain, failed_domains, update_data, should_update_dns)

        if self.config["cleanup_files"]:
            self.write_file(self.config["dns_update_data_file_name"], update_data)
            target_list = []
            # Find all files that match the name pattern for one of our
            # domain name abbreviations
            for target in self.key_names:
                target_list += glob.glob(target + ".*.key") + glob.glob(target + ".*.txt")
            # Go through the update data and remove the entries from target_list that are
            # still referred to by an update_data item.
            for domain_update_data in update_data:
                # if there are insufficient parameters in the object, it is skipped.
                # It needs to have at least a domain name and a selector
                if len(domain_update_data) < 2:
                    self.logger.debug("Skipping domain because of too few parameters")
                    continue

                domain_key = self.domain_data.get(domain_update_data["domain_name"])
                if domain_key is not None:
                    for suffix in [".key", ".txt"]:
                        item_str = domain_key["key"] + "." + domain_update_data["selector"] + suffix
                        try:
                            i = target_list.index(item_str)
                        except:
                            i = -1
                        if i >= 0:
                            del target_list[i]
            # Don't clean entries for domains that failed the DNS update
            for failed_domain in failed_domains:
                domain_key = self.domain_data.get(failed_domain)
                if domain_key is not None:
                    new_list = [x for x in target_list if not x.startswith(domain_key + ".")]
                    target_list = new_list
            # What's left in target_list are just the files that aren't referred to anymore and
            # are eligible for being deleted.
            for filename in target_list:
                self.logger.info("Removing obsolete file %s", filename)
                try:
                    os.remove(filename)
                except:
                    logging.warning("Failed to remove obsolete file %s", filename)
        return failed_domains

    def write_tables(self, key_domain_table, selector, failed_domains):
        """
        Write the domain data and key domain table into key.table and signing.table in the
        format opendkim expects
        """
        def fields_to_line(fields):
            line = ""
            for field in fields:
                if line > 0:
                    line += '\t'
                if isinstance(field, (datetime.datetime, datetime.date)):
                    line += field.strftime('%Y-%m-%dT%H:%M:%S')
                else:
                    line += str(field)
            return line
        key_table_file_name = "key.table"
        signing_table_file = "signing.table"

        if self.config["store_in_new_files"]:
            key_table_file_name += ".new"
            signing_table_file += ".new"

        try:
            key_table_file = open(key_table_file_name, "w")
            signing_table_file = open(signing_table_file, "w")
        except IOError as exception:
            logging.critical("Error creating new key or signing table file")
            self.logger.error("%s", str(exception))
            sys.exit(1)
        # Write the unupdated entries back to the files
        for key_domain, key_domain_data in key_domain_table.items():
            if key_domain in failed_domains:
                self.logger.info("Preserving entries for %s", key_domain)
                try:
                    key_table_file.write("%s\t%s\n" % (key_domain, fields_to_line(key_domain_data)))
                    signing_table_file.write("*@%s\t%s\n" % (key_domain, key_domain_data["api"]))
                except IOError as exception:
                    logging.critical("Error writing new key or signing table file")
                    self.logger.error("%s", str(exception))
                    return False
        # Now write the updated lines to the files
        for domain, domain_data in self.domain_data.items():
            if domain not in failed_domains:
                code = domain.replace(".", "-")
                self.logger.info("Adding entries for %s", domain)
                try:
                    key_table_file.write("%s\t%s:%s:%s/%s.%s.key\n" % \
                                          (code, domain, selector, self.config["opendkim_dir"] + "/keys",
                                           domain_data["key"], selector))
                    signing_table_file.write("*@%s\t%s\n" % (domain, code))
                except IOError as exception:
                    logging.critical("Error writing new key or signing table file")
                    self.logger.error("%s", str(exception))
                    return False
        key_table_file.close()
        signing_table_file.close()
        return True

    def parse_args(self):
        # Set up command-line argument parser and parse arguments
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
                            default="")
        parser.add_argument("--opendkimDir", dest="opendkim_dir", action="store",
                            help="The directory of the opendkim configuration",
                            default="/etc/opendkim")
        parser.add_argument("--key-directory", dest="key_directory", action="store",
                            help="The directory of the opendkim keys directory",
                            default="/etc/opendkim/keys")
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
                            help="Log debugging info and do not update DNS")
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

    def decide_arguments(self):
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

        working_dir = self.args.working_dir
        if "--working-dir" in sys.argv:
            self.logger.debug("Setting working directory from argument")
            self.logger.info("Changing working directory to %s", working_dir)
            os.chdir(working_dir)


        selector = self.args.selector
        if selector is None:
            selector = self.generate_selector()
        else:
            self.logger.info("Selector: %s", selector)
            if self.args.output_selector:

                sys.exit(0)

        return should_update_dns, selector

    def read_files(self):
        self.logger.debug("Reading files")
        self.read_dns_api()
        self.load_dns_api_module_extra_data()

        if not self.read_domain_data():
            sys.exit(1)

    def main(self):

        self.parse_args()

        self.read_config(self.args.config)

        should_update_dns, selector = self.decide_arguments()

        self.overwrite_from_args()

        self.read_files()
        self.key_names = self.get_key_names()

        self.key_data = self.generate_keys(selector)

        key_table_contents = self.read_key_table()

        if key_table_contents is False:
            key_table_contents = {}
        # Check for our DNS API modules. If we don"t have any, there"s no sense in
        # trying to do automatic updating even if we"re supposed to.
        self.dns_apis, should_update_dns_new = self.find_dns_api_modules()
        should_update_dns = should_update_dns and should_update_dns_new
        failed_domains = []
        self.initialize_dns_api_modules()
        failed_domains = self.update_dns(should_update_dns)
        self.finish_dns_api_modules()
        if not self.config["no_write_file"] and self.key_table_length == len(key_table_contents):
            self.logger.info("Generating key and signing tables")
            self.write_tables(key_table_contents, selector, failed_domains)
        else:
            self.logger.info("Not writing key or signing tables")

        self.save_dns_api_module_extra_data()

        sys.exit(0)

if __name__ == "__main__":
    GENKEYS = Genkeys()
    GENKEYS.main()
