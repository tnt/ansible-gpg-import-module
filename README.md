# ansible-gpg-keys-mod

Ansible module to manage GPG-keys.

It addresses the issues of non-responding keyservers in general by repeating attempts and keys.gnupg.net's round-robin-DNS sabotaging DNS-caching (like the Windows DNS-cache does it) in particular by optionally trying alternating hostnames.

### examples

```YAML
tasks:
  - name: Install GPG key
    gpg_keys_mod: key_id="0x3804BB82D39DC0E3" state=present
```
or
```YAML
tasks:
  - name: Install or update GPG key
    gpg_keys_mod:
      key_id: "0x3804BB82D39DC0E3"
      state: latest
      servers:
        - 'hkp://no.way.ever'
        - 'keys.gnupg.net'
        - 'hkps://hkps.pool.sks-keyservers.net'
```
or
```YAML
tasks:
  - name: Install or fail with fake and not fake GPG keys
    gpg_keys_mod:
      key_id: "{{ item }}"
      state: present
      tries: 2
      delay: 0
    with_items:
      - "0x3804BB82D39DC0E3"
      - "0x3804BB82D39DC0E4" # fake key fails
```

### options
name         | default            | description
-------------|:------------------:|-------------
servers      | [ keys.gnupg.net ] | list of hostnames (or `hkp://`/`hkps://` urls) to try
tries        |   3                | number of attempts per *server*
delay        |  0.5               | delay between retries
state        | 'present'          | desired state 'present', 'latest', 'refreshed' or 'absent' ('refreshed' == 'latest')
gpg_timeout  | 5                  | `gpg --keyserver-options timeout=5 ...`


[Strange behaviors](https://gist.github.com/tnt/eedaed9a6cc75130b9cb) occur when used with [insane keys](https://gist.github.com/tnt/70b116c72be11dc3cc66). But this is a gpg-problem.
