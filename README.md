# ansible-gpg-keys-mod

Not yet fully perfect functioning Ansible module to manage GPG-keys.

### examples

```YAML
tasks:
  - name: Install GPG key
    gpg_keys_mod: key_id="0x3804BB82D39DC0E3"
```
or
```YAML
tasks:
  - name: Install GPG key
    gpg_keys_mod:
      key_id: "0x3804BB82D39DC0E3"
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
tries        |   3                | number of attempts per server
delay        |  0.5               |
refresh      | no                 | calls `gpg --refresh-keys ...` - always results in *changed* state
delete       | no                 | calls `gpg --delete-keys ...`


[Strange behaviors](https://gist.github.com/tnt/eedaed9a6cc75130b9cb) occurs when used with [insane keys](https://gist.github.com/tnt/70b116c72be11dc3cc66). But this is a gpg-problem.
