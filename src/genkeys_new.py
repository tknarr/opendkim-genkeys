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
        self.dns_api_data = None
        self.domain_data = None

    def read_config(self, config_path):
        """Reads the configuration from the given configuration path and sets the default
        configuration"""
        # Directory that OpenDKIM key files will be placed in on the mail server
        self.config = {
            "opendkim_dir" : "/etc/opendkim",
            "working_dir" : "",
            "never_update_dns" : False,
            "domain_file_name" : "domains.yml",
            "dns_api_defs_filename" : "dnsapi.yml",
            "dns_update_data_file_name" : "dnsupdate_data.yml",
            "key_table" : "key.table",
            "signing_table" : "signing.table",
            "key_directory" : "/etc/opendkim/keys",
            "cleanup_files" : True,
            "day_difference" : 70,
            "store_in_new_files" : True,
            "no_write_file" : False
        }

        try:
            self.config.update(yaml.safe_load(open(config_path, "r")))
        except Exception as exception:
            logging.warning("Failed to load config from %s, resuming with defaults.", config_path)

    def read_dns_api(self):
        """Reads the dns API configuration file """
        # @returns Bool True if reading succeeded, False if it did not succeed.

        try:
            # dns_api_data files are now yml files, not ini files
            dns_api_data = yaml.safe_load(open(self.config["dns_api_defs_filename"], "r"))
            if not isinstance(dns_api_data, dict):
                raise TypeError("Incorrect file format in file %s, it needs to contain a dict." %
                                self.config["dns_api_defs_filename"])
            else:
                self.dns_api_data = {}
        except Exception as exception:
            self.dns_api_data = {}
            if not self.config["never_update_dns"]:
                logging.critical("Failed to load dns API definitions, aborting!")
                logging.critical("Exception: %s", exception)
                return False
        self.dns_api_data.setdefault("null", [])
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
        print(4)
        try:
            self.domain_data = yaml.safe_load(open(self.config["domain_file_name"], "r"))
        except Exception as exception:
            print(5)
            logging.critical("Failed to load domain configuration, aborting!")
            logging.critical("Exception: %s", exception)
            return False

        if self.domain_data is None:
            logging.critical("No domain definitions found.")
            print(6)
            return False
        # find any domains without configured api and set it to "null"
        print(self.domain_data, 7)
        for domain_data in self.domain_data.values():
            domain_data.setdefault("api", "null")
            domain_data.setdefault("parameters", [])
        print(self.domain_data, 8)
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

            return key_table_entries
        return False

    def read_dns_update_data(self, filename):
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
        logging.debug("dns update data contents %s", file_contents)
        return file_contents

    def get_key_names(self):
        """ Get all key names from the key file """
        key_names = []
        for domain_data in self.domain_data.values():
            print("foo", domain_data)
            key_name = domain_data.get("key")
            if key_name is not None and key_name not in key_names:
                key_names.append(key_name)
        return key_names

    def generate_keys(self, key_names, selector):
        """ Generate all keys """
        generated_key_data = {}
        for key in key_names:
            logging.info("Generating key %s", key)
            key_data = self.generate_singular_key(key, selector)
            if key_data is None:
                logging.critical("Error generating key %s", key)
                return False
            generated_key_data[key] = key_data
        logging.debug("generated key data contents %s", generated_key_data)
        return generated_key_data

    def generate_singular_key(self, key, selector, key_kength=2048):
        """ generate the key pair using openssl rsa """

        private_key_file_name = "{}/{}.{}.key".format(self.config["key_directory"], key,
                                                      selector)
        if not os.path.exists(private_key_file_name):
            logging.info("File %s for selector %s does not exist yet, generating it.",
                         private_key_file_name, selector)
            # file does not exist
            process = subprocess.run(["openssl", "genrsa", "-out", private_key_file_name, "--",
                                      str(key_kength)], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            if process.returncode:
                logging.error(
                    "openssl genrsa failed with returncode %s and the following error output: %s",
                    process.returncode, process.stderr)
                return None
        else:
            logging.warning("Files for %s selector %s already exist", key, selector)

        # convert to public key then generate TXT record, write and use it
        process = subprocess.run(["openssl", "rsa", "-in", private_key_file_name, "-pubout",
                                  "-outform", "PEM"], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)

        if process.returncode:
            logging.error("openssl rsa failed with returncode %s and the following error"
                          "output: %s", process.returncode, process.stderr)
            return None

        # public key is now in stdout, split by newline characters
        lines = process.stdout.decode("utf-8").split("\n")
        # strip first and last line (those are the PEM file format header and trailer)
        public_key_unchunked = " ".join(lines[1:-1])
        # split every 250 characters
        return {
            "selector" : selector,
            "plain" : [public_key_unchunked[i:i+250] for i in range(0, len(public_key_unchunked),
                                                                    250)],
            "chunked" : public_key_unchunked
        }

    def test_dns_servers(self, records, servers):
        """ check if the records can be resolved on all given servers """
        pass

    def test_single_dns_server(self, record, server):
        """ check if the given record can be resolved on the given server """
        pass


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
        # dnsApi.ini file) and for each one X see if we can load a module named
        # dnsApi_X (file will be dnsApi_X.py).
        dns_apis = {}
        possible_names = self.dns_api_data.keys()
        should_update_dns = True

        # Make sure null is included
        if "null" not in possible_names:
            possible_names.append("null")
        for api_name in possible_names:
            module_name = "dnsapi_" + api_name
            try:
                module = importlib.import_module(module_name)
            except ImportError as exception:
                module = None
                logging.error("Module %s for DNS API %s not found", module_name, api_name)
                logging.info("%s", str(exception))
            if module is not None:
                logging.debug("DNS API module %s loaded", api_name)
                dns_apis[api_name] = module
        if len(dns_apis) == 0:
            logging.warning("No DNS API modules found at %s", os.path.dirname(__file__))
            should_update_dns = False

        return dns_apis, should_update_dns

    def cleanup_files(self, update_data, dns_domain_data, key_data, dns_api_module,
                      day_difference):
        """ Remove old records from config files and remove old records from DNS"""
        removed_count = 0
        new_update_data = []
        cutoff = datetime.datetime.now() - datetime.timedelta(day_difference)
        for record in update_data:
            if record["domain"] == dns_domain_data["api"] and record["date"] < cutoff:
                if removed_count == 0:
                    logging.info("Removing old records for %s", dns_domain_data["api"])
                removed_count += 1
                result = dns_api_module.delete(self.dns_api_data[dns_domain_data["api"]]["parameters"],
                                               dns_domain_data, record, self.args.log_debug)
                if result is None:
                    logging.info("No support for removing old record for %s:%s via %s API",
                                 dns_domain_data["api"], record["key"], key_data["dns_api"])
                    # Preserve record if we encountered an error
                    new_update_data.append(record)
                elif result:
                    logging.info("Removing %s:%s created at %s", record["domain"], record["key"],
                                 record["date"].strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    logging.error("Error removing old record for %s:%s via %s API",
                                  record["domain"], record["key"], key_data["dns_api"])
                    # Preserve record if we encountered an error
                    new_update_data.append(record)
        return new_update_data

    def write_file(self, file, data):
        try:
            with open(file, "w") as handle:
                yaml.safe_dump(handle, data)
        except IOError as exception:
            logging.error("Failed to write to %s due to IO exception %s", file, exception)
        except Exception as exception:
            logging.error("Failed to write to %s due to general exception %s", file, exception)

    def update_dns(self, key_names, generated_key_data, dns_apis, should_update_dns):
        update_data = self.read_dns_update_data(self.config["dns_update_data_file_name"])
        failed_domains = []
        if update_data is not None:
            # Convert update data timestamp field to a datetime
            for record in update_data:
                if record.get("date") is not None:
                    record["date"] = datetime.datetime.strptime(record["date"], "%Y-%m-%dT%H:%M:%S")
        else:
            # create dns update data
            try:
                if self.config["store_in_new_files"]:
                    open(self.config["dns_update_data_file_name"] + ".new", "w")
                else:
                    open(self.config["dns_update_data_file_name"], "w")
            except:
                logging.error("Failed to create %s", self.config["dns_update_data_file_name"])

        logging.info("Updating DNS records")
        # Discard records older than 10 weeks (roughly the midpoint of the month 2 months ago),
        # which should retain the last 2 records and discard the 3rd and older record if a monthly
        # rotation is in use.

        failed_domains = []
        for domain, thisdomain_data in self.domain_data.items():
            # work on every domain where an API with parameters is defined (have api and parameters)
            if len(thisdomain_data) == 2:
                dns_api_name = thisdomain_data["api"]
                dns_api_parameters = thisdomain_data["parameters"]
                dns_api_module = None
                # If the null API is to be used, set every domain's API to null or fail
                if self.args.use_null_dnsApi:
                    if "fail" in dns_apis:
                        dns_api_module = dns_apis["fail"]
                    else:
                        dns_api_module = dns_apis["null"]
                else:
                    dns_api_module = dns_apis.get(dns_api_name)

                # if the API is available, apply the update
                if dns_api_module:
                    logging.debug("Found DNS module %s for %s", dns_api_module, domain)
                    dns_api_data = self.dns_api_data[dns_api_name]
                    key_data = generated_key_data[thisdomain_data].copy()

                    if dns_api_data is not None and key_data is not None:
                        key_data["domain"] = domain
                        key_data["dns_api"] = dns_api_name

                        if self.config["cleanup_files"] and update_data is not None:
                            update_data = self.cleanup_files(update_data, thisdomain_data,
                                                             key_data, dns_api_module, 70)

                        # Add new record
                        logging.info("Updating selector %s for %s with key %s",
                                     key_data["selector"], domain, thisdomain_data["key"])
                        if should_update_dns:
                            result = dns_api_module.add(dns_api_data, dns_api_parameters, key_data,
                                                        self.args.log_debug)
                        if result[0]:
                            logging.info("Update succeeded.")
                            records = list(result[1:])
                            if isinstance(update_data, list):
                                update_data.append(records)
                        else:
                            logging.error("Error adding new record for %s with key %s via %s API",
                                          domain, thisdomain_data["key"], dns_api_name)

                            failed_domains.append(domain)
                else:
                    logging.error("Configured DNS API %s of %s not found!", dns_api_name,
                                  thisdomain_data["api"])
                    failed_domains.append(domain)

        if self.config["cleanup_files"]:
            self.write_file(self.config["dns_update_data_file_name"], update_data)

            if self.config["cleanup_files"]:
                target_list = []
                # Find all files that match the name pattern for one of our
                # domain name abbreviations
                for target in key_names:
                    target_list += glob.glob(target + ".*.key") + glob.glob(target + ".*.txt")
                # Go through the update data and remove the entries from target_list that are
                # still referred to by an update_data item.
                for domain_update_data in update_data:
                    # if there are insufficient parameters in the object, it is skipped.
                    # It needs to have at least a domain name and a selector
                    if len(domain_update_data) < 2:
                        logging.debug("Skipping domain because of too few parameters")
                        continue

                    domain_key = self.domain_data.get(domain_update_data["domain"])
                    if domain_key is not None:
                        for suffix in [".key", ".txt"]:
                            item_str = domain_key + "." + domain_update_data[1] + suffix
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
                    logging.info("Removing obsolete file %s", filename)
                    try:
                        os.remove(filename)
                    except:
                        logging.warning("Failed removing obsolete file %s", filename)

        return failed_domains

    def write_tables(self, key_domain_table, selector, failed_domains):
        def fields_to_line(fields):
            line = ""
            for field in fields:
                if line > 0:
                    line += '\t'
                if isinstance(field, datetime.datetime):
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
            logging.error("%s", str(exception))
            sys.exit(1)
        # Write the unupdated entries back to the files
        for key_domain, key_domain_data in key_domain_table.items():
            if key_domain in failed_domains:
                logging.info("Preserving entries for %s", key_domain)
                try:
                    key_table_file.write("%s\t%s\n" % (key_domain, fields_to_line(key_domain_data)))
                    signing_table_file.write("*@%s\t%s\n" % (key_domain, key_domain_data["api"]))
                except IOError as exception:
                    logging.critical("Error writing new key or signing table file")
                    logging.error("%s", str(exception))
                    return False
        # Now write the updated lines to the files
        for domain in self.domain_data.keys():
            if domain not in failed_domains:
                code = domain.replace(".", "-")
                logging.info("Adding entries for %s", domain)
                try:
                    key_table_file.write("%s\t%s:%s:%s/%s.%s.key\n" % \
                                          (code, domain, selector, self.config["opendkim_dir"],
                                           domain, selector))
                    signing_table_file.write("*@%s\t%s\n" % (domain, code))
                except IOError as exception:
                    logging.critical("Error writing new key or signing table file")
                    logging.error("%s", str(exception))
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
        parser.add_argument("--no-dns", dest="update_dns", action="store_false",
                            default=argparse.SUPPRESS,
                            help="Do not update DNS data")
        parser.add_argument("--no-cleanup", dest="cleanup_files", action="store_false",
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
                            help="Do not overwrite old key and signing table files or dnsupdate.yml files, but write new ones")
        parser.add_argument("--version", dest="display_version", action="store_true",
                            help="Display the program version")
        parser.add_argument("selector", nargs="?", default=None, help="Selector to use")
        parser.add_argument("domains", nargs=argparse.REMAINDER, help="List of domains to process")

        self.args = parser.parse_args()
        if self.args.display_version:
            print("OpenDKIM genkeys %s" % self.VERSION)
            sys.exit(0)

    def overwrite_from_args(self):
        if hasattr(self.args, "update_dns"):
            logging.debug("Overwriting updating to dns from args: %s", self.args.update_dns)
            self.config["should_update_dns"] = self.args.update_dns

        if hasattr(self.args, "cleanup_files"):
            logging.debug("Overwriting cleaning up old key files from args: %s", self.args.cleanup_files)
            self.config["cleanup_files"] = self.args.cleanup_files

        if hasattr(self.args, "no_write_file"):
            logging.debug("Overwriting cleaning up old key files from args: %s", self.args.no_write_file)
            self.config["no_write_file"] = self.args.no_write_file
        if hasattr(self.args, "store_in_new_files"):
            logging.debug("Overwriting store_in_new_files from args: %s", self.args.store_in_new_files)
            self.config["store_in_new_files"] = self.args.store_in_new_files
        print(2)

    def decide_arguments(self):
        should_update_dns = self.config["never_update_dns"]

        if self.args.log_debug:
            level = logging.DEBUG
        elif self.args.log_info:
            level = logging.INFO
        else:
            level = logging.WARN

        if self.args.output_selector:
            should_update_dns = False
            level = logging.ERROR

        logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
        if self.args.output_selector:
            logging.debug("Disabling updating DNS because outputting a selector is enabled")
        print(1)
        working_dir = self.args.working_dir
        if "--working-dir" in sys.argv:
            logging.debug("Setting working directory from argument")
            logging.info("Changing working directory to %s", working_dir)
            os.chdir(working_dir)


        selector = self.args.selector
        if selector is None:
            selector = self.generate_selector()
        else:
            logging.info("Selector: %s", selector)
            if self.args.output_selector:
                print(selector)
                sys.exit(0)

        return should_update_dns, selector

    def read_files(self):
        logging.debug("Reading files")
        self.read_dns_api()
        print(3)
        if not self.read_domain_data():
            sys.exit(1)
        print(8)

    def main(self):

        self.parse_args()

        self.read_config(self.args.config)

        self.overwrite_from_args()

        should_update_dns, selector = self.decide_arguments()

        self.read_files()

        key_names = self.get_key_names()
        print(key_names, 9)
        generated_key_data = self.generate_keys(key_names, selector)
        print(generated_key_data)

        # That also gives us the private key and public key txt files needed

        key_table_contents = self.read_key_table()
        if key_table_contents is False:
            key_table_contents = {}

        # Check for our DNS API modules. If we don"t have any, there"s no sense in
        # trying to do automatic updating even if we"re supposed to.
        dns_apis, should_update_dns_new = self.find_dns_api_modules()
        should_update_dns = should_update_dns and should_update_dns_new
        failed_domains = []

        failed_domains = self.update_dns(key_names, generated_key_data,
                                               dns_apis, should_update_dns)
        if not self.config["no_write_file"]:
            logging.info("Generating key and signing tables")
            self.write_tables(key_table_contents, selector, failed_domains)
        else:
            logging.info("Not writing key or signing tables")

        sys.exit(0)

if __name__ == "__main__":
    GENKEYS = Genkeys()
    GENKEYS.main()
