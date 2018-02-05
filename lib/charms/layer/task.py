import os
from tempfile import NamedTemporaryFile

from ansible.executor import playbook_executor
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.utils.display import Display
from ansible.vars.manager import VariableManager


class Options(object):
    """
    Options class to replace Ansible OptParser
    """

    def __init__(self, verbosity=None,
                 inventory=None,
                 listhosts=None,
                 subset=None,
                 module_paths=None,
                 extra_vars=None,
                 forks=1,
                 ask_vault_pass=None,
                 vault_password_files=None,
                 new_vault_password_file=None,
                 output_file=None,
                 tags=None,
                 skip_tags=[],
                 one_line=None,
                 tree=None,
                 ask_sudo_pass=None,
                 ask_su_pass=None,
                 sudo=None,
                 sudo_user=None,
                 become=None,
                 become_method=None,
                 become_user=None,
                 become_ask_pass=None,
                 ask_pass=None,
                 private_key_file=None,
                 remote_user=None,
                 connection=None,
                 timeout=None,
                 ssh_common_args=None,
                 sftp_extra_args=None,
                 scp_extra_args=None,
                 ssh_extra_args=None,
                 poll_interval=None,
                 seconds=None,
                 check=None,
                 syntax=None,
                 diff=None,
                 force_handlers=None,
                 flush_cache=None,
                 listtasks=None,
                 listtags=[],
                 module_path=None):
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.vault_password_files = vault_password_files
        self.new_vault_password_file = new_vault_password_file
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.syntax = syntax
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.module_path = module_path


class Runner(object):

    def __init__(self,
                 playbooks,
                 tags,  # must have
                 listtags=[],
                 extra_vars={},
                 hostnames='127.0.0.1',
                 connection='local',  # smart|ssh|local
                 private_key_file='',
                 become_pass='',
                 vault_pass='',
                 verbosity=0):

        self.options = Options()
        self.options.tags = tags,
        self.options.listtags = listtags,
        self.options.private_key_file = private_key_file
        self.options.verbosity = verbosity
        self.options.connection = connection
        self.options.become = True
        self.options.become_method = 'sudo'
        self.options.become_user = 'root'
        self.options.extra_vars = extra_vars

        # Set global verbosity
        self.display = Display()
        self.display.verbosity = self.options.verbosity

        # Executor appears to have it's own
        # verbosity object/setting as well
        playbook_executor.verbosity = self.options.verbosity

        # Become Pass Needed if not logging in as user root
        passwords = {'become_pass': become_pass}

        # Gets data from YAML/JSON files
        self.loader = DataLoader()
        self.loader.set_vault_secrets(vault_pass)
        # Parse hosts, I haven't found a good way to
        # pass hosts in without using a parsed template :(
        # (Maybe you know how?)
        self.hosts = NamedTemporaryFile(delete=False, mode='wt')
        self.hosts.write("""[run_hosts]\n%s""" % hostnames)
        self.hosts.close()

        # This was my attempt to pass in hosts directly.
        #
        # Also Note: In py2.7, "isinstance(foo, str)" is valid for
        #            latin chars only. Luckily, hostnames are
        #            ascii-only, which overlaps latin charset
        # if isinstance(hostnames, str):
        # hostnames = {"customers": {"hosts": [hostnames]}}

        # Set inventory, using most of above objects
        self.inventory = InventoryManager(
            loader=self.loader, sources=[self.hosts.name])

        # All the variables from all the various places
        self.variable_manager = VariableManager(loader=self.loader,
           inventory=self.inventory)

        self.variable_manager.extra_vars = extra_vars

        # Playbook to run. Assumes it is
        # local and relative to this python file
        # in "../../../playbooks" directory.
        dirname = os.path.dirname(__file__) or '.'
        pb_rel_dir = '../../../playbooks'
        pb_dir = os.path.join(dirname, pb_rel_dir)
        self.options.module_path = os.path.join(pb_dir, 'library')

        # os.environ['ANSIBLE_CONFIG'] = os.path.abspath(os.path.dirname(__file__))

        # pbs = ["%s/%s" % (pb_dir, pb) for pb in playbooks]
        pbs = [os.path.join(pb_dir, pb) for pb in playbooks]

        # Setup playbook executor, but don't run until run() called
        self.pbex = playbook_executor.PlaybookExecutor(
            playbooks=pbs,
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=passwords)

    def run(self):
        # Results of PlaybookExecutor
        self.pbex.run()
        stats = self.pbex._tqm._stats

        # Test if success for record_logs
        run_success = True
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            if t['unreachable'] > 0 or t['failures'] > 0:
                run_success = False

        # Dirty hack to send callback to save logs with data we want
        # Note that function "record_logs" is one I created and put into
        # the playbook callback file
        # self.pbex._tqm.send_callback(
        #     'record_logs',
        #     user_id=self.extra_vars['user_id'],
        #     success=run_success
        # )

        # Remove created temporary files
        os.remove(self.hosts.name)

        return stats
