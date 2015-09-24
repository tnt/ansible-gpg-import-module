#!/usr/bin/python
# -*- coding: utf-8 -*-
# © Thelonius Kort - Feel free to redistribute this with any MIT, GPL, or Apache License

from time import sleep
import re

DOCUMENTATION = '''
---
module: gpg_import
version_added: 1.9
short_description:  Manages import and removal of GPG-keys
description:
     - Imports, refreshes, and deletes GnuPG keys. When importing or refreshing a key it retries on
       failure and optionally retries with alternating hostnames to fudge on DNS-caches that prevent
       round-robin keyservers.
options:
  key_id:
    description:
      - "The id of the key to be imported"
    required: true
    default: null

  state:
    description:
      - Whether to import (C(present), C(latest)), or remove (C(absent)) a key. C(refreshed) is an alias for C(latest).
    required: false
    choices: [ "present", "latest", "refreshed",  "absent" ]
    default: "present"

  servers:
    description:
      - A list of hostnames (or `hkp://`/`hkps://` urls) to try
    required: false
    default: "['keys.gnupg.net']"

  tries:
    description:
      - How often to try per server
    required: false
    default: 3
    aliases: []

  delay:
    description:
      - Delay between retries
    required: false
    default: 0.5

  gpg_timeout:
    description:
      - Timeout parameter for gpg
    required: false
    default: 5

notes: []
requirements: [ gpg ]
author: Thelonius Kort
'''

EXAMPLES = '''
- name: Install GPG key
  gpg_import: key_id="0x3804BB82D39DC0E3" state=present
- name: Install or update GPG key
  gpg_import:
    key_id: "0x3804BB82D39DC0E3"
    state: latest
    servers:
      - 'hkp://no.way.ever'
      - 'keys.gnupg.net'
      - 'hkps://hkps.pool.sks-keyservers.net'
- name: Install or fail with fake and not fake GPG keys
  gpg_import:
'''

class GpgImport(object):

    def __init__(self, module):
        self.m = module
        self._setup_creds()
        self._execute_task()

    def _execute_task(self):
        res = self._execute_command('check')
        key_present = res['rc'] == 0

        if key_present and self.state == 'absent':
            res = self._execute_command('delete')
            self.changed = res['rc'] == 0
        elif key_present and self.state in ('latest','refreshed'):
            res = self._repeat_command('refresh')
            self.changed = re.search('gpg:\s+unchanged: 1\n', res['stderr']) is None
        elif not key_present and self.state in ('present','latest','refreshed'):
            res = self._repeat_command('recv')
            self.changed = res['rc'] == 0
        else:
            self.changed = False
            res = {'rc': 0}

        if res['rc'] != 0:
            self.m.fail_json(msg=self.log_dic)


    def _setup_creds(self):
        for k,v in self.m.params.items():
            setattr(self, k, v)
        self.commands = {
            'check':   '%s %s --list-keys %s',
            'delete':  '%s %s --batch --yes --delete-keys %s',
            'refresh': '%s %s --keyserver %%s --keyserver-options timeout=%%d --refresh-keys %s',
            'recv':    '%s %s --keyserver %%s --keyserver-options timeout=%%d --recv-keys %s'
        }
        bp = self.m.get_bin_path('gpg', True)
        check_mode = '--dry-run' if self.m.check_mode else ''
        for c,l in self.commands.items():
            self.commands[c] = l % (bp, check_mode, self.key_id)
        self.urls = [s if re.match('hkps?://', s)
                       else 'hkp://%s' % s
                     for s in self.servers]

    def _repeat_command(self, cmd):
        for n in range(self.tries):
            for u in self.urls:
                args = (u, self.gpg_timeout)
                raw_res = self.m.run_command(self.commands[cmd] % args)
                res = self._legiblify(cmd, raw_res)
                if res['rc'] == 0:
                    return res
                sleep(self.delay)
        return {'rc': 8888}

    def _execute_command(self, cmd):
        raw_res = self.m.run_command(self.commands[cmd])
        return self._legiblify(cmd, raw_res)

    def _legiblify(self, sec, res):
        """turn tuple to dict and preserve it for debugging"""
        if not hasattr(self, 'log_dic'):
            self.log_dic = {}
        rdic = dict([k, res[i]] for i,k in enumerate(('rc', 'stdout', 'stderr')))
        self.log_dic.setdefault(sec, {'tries': [], 'num_tries':  0})
        self.log_dic[sec]['tries'].append(rdic)
        self.log_dic[sec]['num_tries'] += 1
        return rdic


def main():
    module = AnsibleModule(
        argument_spec = dict(
            key_id=dict(required=True, type='str'),
            servers=dict(default=['keys.gnupg.org'], type='list'),
            tries=dict(default=3, type='int'),
            delay=dict(default=0.5),
            state=dict(default='present', choices=['latest', 'refreshed', 'absent', 'present']),
            gpg_timeout=dict(default=5, type='int')
        ),
        supports_check_mode=True
    )

    gkm = GpgImport(module)

    result = {'log_dic': gkm.log_dic,
              'changed': gkm.changed}

    module.exit_json(**result)


from ansible.module_utils.basic import *
main()
