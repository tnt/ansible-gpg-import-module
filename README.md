# ansible-gpg-keys-mod

Not yet fully functioning Ansible module to manage GPG-keys.

### examples

```YAML
tasks:
  - name: Install GPG key
    gpg_keys_mod: key_id=409B6B1796C275462A1703113804BB82D39DC0E3
```
or
```YAML
tasks:
  - name: Install GPG key
    gpg_keys_mod:
      key_id: "409B6B1796C275462A1703113804BB82D39DC0E3"
      servers:
        - 'hkp://no.way.ever'
        - 'keys.gnupg.net'
        - 'hkps://hkps.pool.sks-keyservers.net'
      tries: 3
      delay: 0
```

### options
name         | default            | description
-------------|:------------------:|-------------
servers      | [ keys.gnupg.net ] | list of hostnames (or `hkp://`/`hkps://` urls) to try
tries        |   3                | number of attempts per server
delay        |  0.5               |
refresh      | no                 | calls `gpg --refresh-keys ...` - always results in *changed* state
delete       | no                 | calls `gpg --delete-keys ...`


At the current stage [strange behavior](https://gist.github.com/tnt/eedaed9a6cc75130b9cb) occurs when used combined with `with_items`. Probably I have to learn more about ansible modules...
