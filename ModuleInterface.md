# DNS module interface definition

Copyright &copy; 2016 Todd T Knarr &lt;tknarr@silverglass.org&gt;

## Functions

-   `add`: Adds a new DNS record for a new selector value, returns API-specific data
    identifying the record.
-   `delete`: Deletes a specific DNS record.

## Function details

### `init`

This function gets executed before any module API add or delete calls are done.
It can be used to manipulate the `module_specific_data` structure.

**Arguments**

-   `module_specific_data`: An dict in which arbitrary data can be stored and passed between
    Module API calls

### `finish`

This function gets executed after when genkeys.py terminates. It can be used to clean up
the module specific data before it is stored in the dns api extra data yaml file.

**Arguments**

-   `module_specific_data`: An dict in which arbitrary data can be stored and passed between
    Module API calls

### `add`

Adds a new DomainKeys TXT record to a domain using a selector value (normally set based on
the current year and month). Due to the way TXT records work it's possible to end up with
multiple records for the same selector value, which can be a problem to clean up. For that
reason the software records the identifying data returned by the DNS provider for each
record it adds, allowing exact control over which record is accessed once it's created.

**Arguments**

-   `dnsapi_data`: Information from `dnsapi.ini` for the domain.
-   `dnsapi_domain_data`: Information from `domains.ini` for the domain.
-   `key_data`: Data about the generated key created by `genkeys.py`.
-   `module_specific_data`: An dict in which arbitrary data can be stored and passed between
    Module API calls
-   `debugging`: Normally omitted, defaults to False if omitted. If given as True, causes
    DNS modules to return before actually doing anything and may cause additional diagnostic
    output.

**Return value**

Module-specific tuple containing sufficient information to identify the new record added
to DNS for a specific domain and selector value.

-   Boolean indication of whether the operation succeeded or failed. If false, the remaining
    items in the tuple may not be present.
-   Domain for record.
-   Selector value for record.
-   UTC timestamp when record was created.
-   Additional module-specific items. Exact content varies by API module but usually includes
    at least the record ID.

### `delete`

Deletes a specific DomainKeys TXT record from a domain. This is based on identifiers set
by the DNS provider when the record is created, allowing it to distinguish between multiple
TXT records for the same selector value.

**Arguments**

*TODO*

**Return value**

True or False depending on whether the operation succeeded or failed. If the API module doesn't
support the delete operation, None may be returned which causes `genkeys.py` to retain the
update data and related files and print an informational message rather than an error.
