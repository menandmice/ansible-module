# Ansible modules

## mm_claimip

Claim IP addresses in DHCP in the Men&Mice Suite

### Options

- `customproperties`: Custom properties for the IP address.
  These properties must already exist See also `mm_props`
- `ipaddress`: (required) The IP address(es) to work on
- `provider`: (required) Definition of the Men&Mice suite API provider
- `state`: The state of the claim (`absent`, `present`)

## mm_dhcp

Manage DHCP reservations on the Men&Mice Suite

### Options

- `ddnshost`: The dynamic DNS host to place the entry in
- `deleteunspecified`: Clear properties that are not explicitly set
- `filename`: Filename to place the entry in
- `ipaddress`: (required) The IP address(es) to make a reservation on.
  When the IP address is changed a new reservation is made.
  It is not allowed to make reservations in DHCP blocks
- `macaddress`: (required) MAC address for the IP address
- `name`: (required) Name of the reservation
- `nextserver`: Next server as DHCP option (bootp)
- `provider`: (required) Definition of the Men&Mice suite API provider
- `servername`: Server to place the entry in
- `state`: The state of the reservation (`absent`, `present`)

## mm_dnsrecord

Manage DNS records in the Men&Mice Suite

### Options

- `aging`: The aging timestamp of dynamic records in AD integrated
  zones. Hours since January 1, 1601, UTC. Providing a non-zero value
  creates a dynamic record
- `comment`: Comment string for the record. Note that only records in
  static DNS zones can have a comment string
- `data`: (required) The record data in a tab-separated list
- `dnszone`: (required) The DNS zone where the action should take place
- `enabled`: True if the record is enabled. If the record is disabled
  the value is false
- `name`: (required) The name of the DNS record. Can either be partially
  or fully qualified
- `provider`: (required) Definition of the Men&Mice suite API provider
- `rrtype`: RR Type for the IP address
  `A`, `AAAA`, `CNAME`, `DNAME`, `DLV`, `DNSKEY`, `DS`, `HINFO`, `LOC`,
  `MX`, `NAPTR`, `NS`, `NSEC3PARAM`, `PTR`, `RP`, `SOA`, `SPF`, `SRV`,
  `SSHFP`, `TLSA`, `TXT`
- `state`: The state of the properties or properties (`absent`, `present`)
- `ttl`: Specifies the Time-To-Live of the DNS record

## mm_ipprops

Set properties on an IP address in the Men&Mice Suite

### Options

- `deleteunspecified`: Clear properties that are not explicitly set
- `ipaddress`: (required) The IP address(es) to work on
- `properties`: (required) Custom properties for the IP address
  These properties must already be defined. See also `mm_props`
- `provider`: (required) Definition of the Men&Mice suite API provider
- `state`: Property present or not (`absent`, `present`)

## mm_props

Manage custom properties in the Men&Mice Suite

### Options

- `cloudtags`: Associated cloud tags
- `defaultvalue`: Default value of the property
- `dest`: (required) Where to define the custom property
  `dnsserver`, `dhcpserver`, `zone`, `iprange`, `ipaddress`, `device`,
  `interface`, `cloudnet`, `cloudaccount`
- `listitems`: The items in the selection list.
- `mandatory`: Is the property mandatory
- `multiline`: Is the property multiline
- `name`: (required) Name of the property
- `proptype`: Type of the property.
  These are not the types as described in the API, but the types as you
  can see them in the Men&Mice Management Console
  `text`, `yesno`, `ipaddress`, `number`
- `provider`: (required) Definition of the Men&Mice suite API provider
- `readonly`: Is the property read only
- `state`: The state of the properties or properties (`absent`, `present`)
- `system`: Is the property system defined
- `updateexisting`: Should objects be updated with the new values.
  Only valid when updating a property, otherwise ignored

## mm_zone

Manage DNS zones in the Men&Mice Suite

### Options

- `adintegrated`: True if the zone is Active Directory integrated
- `adpartition`: The AD partition if the zone is Active Directory
  integrated
- `adreplicationtype`: Type of the AD replication
- `authority`: Name of the DNS server that contains the zone or the
  string `[Active Directory]` if the zone is AD integrated
- `customproperties`: Custom properties for the zone.
  These properties must already exist. See also `mm_props`
- `dnssecsigned`: True if the zone is a DNSSEC signed zone
- `dynamic`: Dynamic DNS zone
- `kskids`: A comma separated string of IDs of KSKs, starting with
  active keys, then inactive keys in parenthesis
- `masters`: The IP addresses of the master servers if the new zone is
  not a master zone.
- `name`: (required) Name of the zone
- `nameserver`: (required) Nameserver to define the zone on
- `provider`: (required) Definition of the Men&Mice suite API provider
- `servtype`: Type of the master server
  `master`, `slave`, `stub`, `forward`
- `state`: The state of the zone (`absent`, `present`)
- `zskids`: A comma separated string of IDs of ZSKs, starting with
  active keys, then inactive keys in parenthesis
