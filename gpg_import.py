#!/usr/bin/python
# -*- coding: utf-8 -*-
# © Thelonius Kort - Feel free to redistribute this with any MIT, GPL, or Apache License

from time import sleep
import re
import string

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
      - The id of the key to be fetched and imported. Only applicable to private keys (for now). Either key_file or key_id is required.
    required: false
    default: null

  key_file:
    description:
      - Filename of key to be imported. Must be on remote machine, not local. Only applicable to public keys (for now). Either key_file or key_id is required.
    required: false
    default: null

  key_type:
    description:
      - What type of key to import.
    required: true
    choices: [ "private", "public" ]
    default: "private"

  bin_path:
    description:
      - "Location of GPG binary"
    require: false
    default: /usr/bin/gpg

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

- name: import a file-based public key
  gpg_import: key_type=public state=present key_file=/etc/customer-key/customer.pubkey

- name: import a file-based private key
  gpg_import: key_type=private state=present key_file=/etc/customer-key/customer.privatekey
'''

class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

# http://stackoverflow.com/a/33621609/659298
class SafeFormatter(string.Formatter):
    def __init__(self, default='{{{0}}}'):
        self.default=default

    def get_value(self, key, args, kwds):
        if isinstance(key, str):
            return kwds.get(key, self.default.format(key))
        else:
            string.Formatter.get_value(key, args, kwds)

class GpgImport(object):

    def __init__(self, module):
        self.m = module
        self.debuglist = []
        self._setup_creds()
        self._execute_task()

    def _debug(self, msg):
        # named 'debuglist' to avoid 'self.debug()' attempting to work.
        self.debuglist.append(msg)

    def _execute_task(self):
        key_present = False
        if self.key_type == 'public':
            filekey = self._get_key_from_file()
            if filekey:
                # rerun the original setup with this key in the commands
                self._setup_creds(filekey)
                res = self._execute_command('check-public')
                self._debug('checkpublic: %s' % (str(res)))
                key_present = res['rc'] == 0
        elif self.key_type == 'private':
            filekey = self._get_key_from_file()
            if filekey:
                # rerun the original setup with this key in the commands
                self._setup_creds(filekey)
                res = self._execute_command('check-private')
                self._debug('checkprivate: %s' % (str(res)))
                key_present = res['rc'] == 0
        else:
            res = self._execute_command('check')
            key_present = res['rc'] == 0

        if key_present and self.state == 'absent':
            res = self._execute_command('delete')
            self.changed = res['rc'] == 0
        elif key_present and self.state in ('latest','refreshed'):
            res = self._repeat_command('refresh')
            self.changed = re.search('gpg:\s+unchanged: 1\n', res['stderr']) is None
        elif not key_present and self.state in ('present','latest','refreshed'):
            if self.key_type == 'private':
                if self.key_file:
                    res = self._execute_command('import-key')
                    self._debug('running i-private')
                else:
                    self._debug('running recv')
                    res = self._repeat_command('recv')
            elif self.key_type == 'public':
                res = self._execute_command('import-key')
                self._debug('running i-public')
            self.changed = res['rc'] == 0
        #elif key_present and self.state == 'xxxxxx':
        #    res = self._execute_command('xxxxxx')
        #    self.changed = res['rc'] == 0
        else:
            self.changed = False
            res = {'rc': 0}

        if res['rc'] != 0:
            self.m.fail_json(msg=self.log_dic, debug=self.debuglist)


    def _setup_creds(self, key_override=None):
        for k,v in self.m.params.items():
            setattr(self, k, v)
        if key_override:
            self.key_id = key_override
        self.commands = {
            'check':   '{bin_path} {check_mode} --list-keys {key_id}',
            'delete':  '{bin_path} {check_mode} --batch --yes --delete-keys {key_id}',
            'refresh': '{bin_path} {check_mode} --keyserver {url} --keyserver-options timeout={timeout} --refresh-keys {key_id}',
            'check-private':  '{bin_path} {check_mode} --list-secret-keys {key_id}',
            'recv':    '{bin_path} {check_mode} --keyserver {url} --keyserver-options timeout={timeout} --recv-keys {key_id}',
            'check-public':  '{bin_path} {check_mode} --list-public-keys {key_id}',
            'import-key': '{bin_path} {check_mode} --import {key_file}'
        }
        command_data = {
            'check_mode': '--dry-run' if self.m.check_mode else '',
            'bin_path': self.m.get_bin_path(self.bin_path, True),
            'key_id': self.key_id,
            'key_file': self.key_file
        }
        # sort of a brilliant way of late-binding/double-formatting given here: http://stackoverflow.com/a/17215533/659298
        for c,l in self.commands.items():
            sf = SafeFormatter()
            self.commands[c] = sf.format(l, **command_data)
        self.urls = [s if re.match('hkps?://', s)
                       else 'hkp://%s' % s
                     for s in self.servers]
        self._debug('set up commands: %s' % (str(self.commands)))

    def _repeat_command(self, cmd):
        for n in range(self.tries):
            for u in self.urls:
                sf = SafeFormatter()
                full_command = sf.format(
                    self.commands[cmd], timeout=self.gpg_timeout, url=u
                )
                self._debug("full command: %s" % (full_command))
                raw_res = self.m.run_command(full_command)
                res = self._legiblify(cmd, raw_res)
                if res['rc'] == 0:
                    return res
                sleep(self.delay)
        return {'rc': 8888}

    def _execute_command(self, cmd):
        self._debug('command: %s' % (str(self.commands[cmd])))
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

    def _get_key_from_file(self):
        keycmd = '%s --dry-run --import %s'
        bp = self.m.get_bin_path(self.bin_path, True)
        print(bp, self.key_file)
        keycmd_expanded = keycmd % (bp, self.key_file)
        self.changed = False
        raw_res = self.m.run_command(keycmd_expanded)
        keyinfo = raw_res[2]
        self._debug('keyinfo: %s' % (str(keyinfo)))
        # keyinfo: gpg: key 32382FA0: \"Pau
        keysearch = re.match(r'gpg:\s+key\s+([0-9A-F]+):', keyinfo)

        if keysearch and keysearch.group(1):
            self._debug('keysearch groups: %s' % (str(keysearch.groups())))
            return keysearch.group(1)
        return None

def main():
    module = AnsibleModule(
        argument_spec = dict(
            key_id=dict(required=False, type='str'),
            key_file=dict(required=False, type='str'),
            servers=dict(default=['keys.gnupg.net'], type='list'),
            bin_path=dict(default='/usr/bin/gpg', type='str'),
            tries=dict(default=3, type='int'),
            delay=dict(default=0.5, type='float'),
            state=dict(default='present', choices=['latest', 'refreshed', 'absent', 'present']),
            key_type=dict(default='private', choices=['private', 'public']),
            gpg_timeout=dict(default=5, type='int')
        ),
        supports_check_mode=True,
        required_one_of=[['key_id', 'key_file']]
    )

    gkm = GpgImport(module)

    result = {
        'log_dic': gkm.log_dic,
        'changed': gkm.changed,
        'debug': gkm.debuglist
    }

    module.exit_json(**result)


from ansible.module_utils.basic import *
main()
