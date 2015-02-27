#!/usr/bin/python
# -*- coding: utf-8 -*-

from time import sleep
import re

class GpgKeysMod(object):

    def __init__(self, module):
        self.m = module
        self.setup_creds()
        self.set_urls()

    def set_urls(self):
        self.urls = [s if re.match('hkps?://', s)
                       else 'hkp://%s' % s
                     for s in self.servers]

    def setup_creds(self):
        for k,v in self.m.params.items():
            setattr(self, k, v)
        self.commands = {
            'check':   '%s --list-keys %%s',
            'delete':  '%s --batch --yes --delete-keys %%s',
            'refresh': '%s --keyserver %%s --refresh-keys %%s',
            'recv':    '%s --keyserver %%s --recv-keys %%s'
        }
        bp = self.m.get_bin_path('gpg', True)
        for c,l in self.commands.items():
            self.commands[c] = l % bp
        self.c_results = dict([k, {'tries': [], 'num_tries':  0}] for k in self.commands)

    def repeat_command(self, cmd):
        for n in range(self.tries):
            for u in self.urls:
                res = self.m.run_command(self.commands[cmd] % (u, self.key_id))
                self._to_c_results(cmd, res)
                sleep(self.delay)
                if res[0] == 0:
                    return 0

    def execute_command(self, cmd):
        res = self.m.run_command(self.commands[cmd] % self.key_id)
        self._to_c_results(cmd, res)
        return res[0]

    def _to_c_results(self, sec, res):
        rdic = dict([k, res[i]] for i,k in enumerate(('rc', 'stdout', 'stderr')))
        self.c_results[sec]['tries'].append(rdic)
        self.c_results[sec]['num_tries'] += 1


def main():
    module = AnsibleModule(
        argument_spec = dict(
            key_id=dict(required=True, type='str'),
            servers=dict(default=['keys.gnupg.org'], type='list'),
            tries=dict(default=3, type='int'),
            delay=dict(default=0.5),
            refresh=dict(default=False, type='bool'),
            delete=dict(default=False, type='bool')
        ),
        supports_check_mode=True
    )

    changed = False
    gkm = GpgKeysMod(module)

    if gkm.refresh and gkm.delete:
        module.fail_json(msg='delete and refresh are exclusive')

    key_present = gkm.execute_command('check') == 0

    if not key_present and module.check_mode:
        changed = True
    else:
        rc = None
        if key_present and gkm.refresh and not module.check_mode:
            rc = gkm.repeat_command('refresh')
        elif key_present and gkm.delete and not module.check_mode:
            rc = gkm.execute_command('delete')
        elif not key_present and not module.check_mode:
            rc = gkm.repeat_command('recv')
            if rc != 0:
                module.fail_json(msg=gkm.c_results['recv'])
        if rc == 0:
            changed = True

    result = {'c_results': gkm.c_results,
              'changed': changed}

    module.exit_json(**result)


from ansible.module_utils.basic import *
main()
