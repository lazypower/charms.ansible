# charms.ansible

Do you have existing ansible playbooks you want to use in Juju Charms? This
library works in tandem with `layer:ansible` to deliver a consistent Ansible with
juju experience. Just bring your playbooks and operational knowledge.

This library offers two methods: method 1 is based on calling
`ansible-playbook` CLI, where method 2 is using [Ansible Python API][6].

# Method 1

## Install Ansible

This module handles installing ansible from `ppa:ansible/ansible` by default.
This is tuneable when calling install_ansible to point to a different PPA if
required

```python
from charms.ansible import install_ansible_support

@when_not('ansible.available')
def bootstrap_with_ansible():
   install_ansible_support('ppa:rquillo/ansible')
```

## Run a playbook

By default, ansible is setup to apply against `localhost`. By this convention
we also have a cache of all the unit data that `charms.ansible` is aware of in
`/etc/ansible/host_vars/localhost`. Additionally, playbooks are executed
filtered by tags when you need to group actions to a similar event.


#### Run a simple playbook

This code would reside in your charms reactive module: `reactive/somefile.py`

```python
from charms.ansible import apply_playbook

@when('ansible.available')
def run_playbook():
    apply_playbook('files/playbook.yaml')
```

#### Example: `files/playbook.yaml`

Invoking Ansible against this yaml

```yaml
- hosts: localhost
  vars:
    - service_name: "{{ local_unit.split('/')[0] }}"
  tasks:
    - include: tasks/install-widgets.yml
      tags:
        - ansible.available
```

Notice the filter of `tags` - Tags are executed in `or` fashion by default. Meaning
if any tags match, the associated play is executed.

> **Caveat** - Due to this pattern, if you attempt to apply_playbook() on a playbook
that is tagged, and there is no matching tag in the environment, it will raise
an error. Great care should be taken to not encounter codepaths in this nature.


## Use Configuration in an Ansible based charm

Charm configuration is passed implicitly into rendering contexts when called
from an Ansible playbook, and can be referenced directly.

### Examples

### Configuration

Example config.yaml

```yaml
options:
  version_number:
    type: string
    default: v2.0.15
    description: Version number of widget to fetch
  profile:
    type: string
    default: fast
    description: Deployment profile to render
```

Example `tasks/install_widgets.yaml`
for inline config variable expansion

```yaml
tasks:
  - include: tasks/install_widget_{{version_number}}.yaml
    tags:
      - widget.notinstalled
  - name: Update configuration
    template: src={{ charm_dir }}/templates/widget_config.toml
              dest=/etc/widget/config.yml
              mode=0644
              backup=yes
    notify:
      - Restart Widget
```

Example `templates/widget_config.toml` - Jinja2 template can make direct reference
to config in the template being rendered, when invoked from an ansible
`template` play.

```jinja2
{% if profile %}
tuning_profile={{ profile }}
{% endif %}
```
## Credit

This library is heavilly based (right now its a direct fork) of mnelson's work
on charmhelpers.contrib.ansible module. Charms have evolved a long way since
that was a 'gold standard'. This is an attempt at resurrecting that work and
continuing the learning of using Ansible in Juju.

Major thanks to the early contributors, bug filers, and adopters of this great
library. This wouldn't be possible without it!

# Method 2

Design objectives:

1. Design as reusable [layer(s)][1]
2. Be compatible with Ubuntu and CentOS
3. Simple pattern to execute a playbook

[1]: https://jujucharms.com/docs/2.1/developer-layers

Assumption:

1. Playbooks will be local (in charm) so to maintain the
   atomic nature of a HW charm &mdash; the model contains both the
   declaration of attributes and actions to handle runtime state transitions.


This method is inspired by [this article][5]. This is to take
advantage of the [Ansible Python API][6]. 

[5]: https://serversforhackers.com/running-ansible-2-programmatically
[6]: http://docs.ansible.com/ansible/dev_guide/developing_api.html

## Design details

1. Install prerequisites. Installing `Ansible` will fail on a vanilla
   Ubuntu because it misses a few dependencies. Using [layer-basic][7]
   by listing them out in `layer.yaml`:


     ```yaml
     includes:
       - 'layer:basic'
     options:
       basic:
         packages:
           - libffi-dev
           - libssl-dev
           - python
           - python3-dev
      ```

[7]: https://github.com/juju-solutions/layer-basic

2. Install Ansible.  Use Python [wheel][8] supported
   by [layer-basic][7]. In `wheelhouse.txt`:

[8]: https://packaging.python.org/discussions/wheel-vs-egg/?highlight=wheel

      ```
      ansible==2.4.2
      ```

3. `ansible.cfg`. Instead of using a global config, this is local so
   each charm can have its own variation if desired.

      ```
      [defaults]
      inventory = ./hosts
      log_path = /var/log/ansible/ansible.log
      remote_tmp = $HOME/.ansible/tmp
      local_tmp = $HOME/.ansible/tmp
      
      [ssh_connection]
      ssh_args = -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -o ControlMaster=auto -o ControlPersist=60s
      control_path = ~/.ansible/cp/ansible-ssh-%%h-%%p-%%r
      ```

4. Options. Constructed a class to be the abstraction of Ansible
   options:

      ```python
      class Options(object):
          """
          Options class to replace Ansible OptParser
          """
          ....
          verbosity=None,
          inventory=None,
          listhosts=None,
          subset=None,
          module_paths=None,
          extra_vars=None,
          forks=None,
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
          module_path=None
      ```

5. Playbook execution. Running it is to use
   Ansible's API call `PlaybookExecutor`.

      ```python
      self.pbex = playbook_executor.PlaybookExecutor(
          playbooks=pbs,
          inventory=self.inventory,
          variable_manager=self.variable_manager,
          loader=self.loader,
          options=self.options,
          passwords=passwords)
      ....
      self.pbex.run()
      ```

## Charm integration

Integrating with charm takes the followings:

1. Include layer. In `layer.yaml`:

      ```yaml
      includes:
        - 'layer:basic'
        - 'layer:ansible'
      ```

2. Create a `playbooks` folder and place playbooks here:

      ```
      .
      ├── config.yaml
      ├── icon.svg
      ├── layer.yaml
      ├── metadata.yaml
      ├── playbooks
      │   └── test.yaml
      └── reactive
          └── solution.py
      ```

3. Using `config.yaml` to pass in playbook for each action that is
   defined in the charm states. For example, define `test.yaml` for an
   action in `state-0`:

      ```yaml
      options:
        state-0-playbook:
          type: string
          default: "test.yaml"
          description: "Playbook for..."
      ```

4. Define the playbook. For example, a _hello world_ that will create
   a file `/tmp/testfile.txt'.

      ```yaml
      - name: This is a hello-world example
        hosts: 127.0.0.1
        tasks:
        - name: Create a file called '/tmp/testfile.txt' with the content 'hello world'.
          copy: content="hello world\n" dest=/tmp/testfile.txt
          tags:
            - sth
      ```

    Note that `tags` value `sth` must match playbook run call (see
    below).

5. In charm `.py` file, `from charms.layer.task import Runner`, then
   in `state-0` to call given playbook:

      ```python
      playbook = config['state-0-playbook']
      runner = Runner(
          tags = 'sth', # <-- must match the tag in the playbook
          connection = 'local', # <-- must be "local"
          hostnames = '127.0.0.1', # <-- assuming execution in localhost
          playbooks = [playbook],
          private_key_file = '',
          run_data = {},
          become_pass = '',
          verbosity = 0
      )
      stats = runner.run()
      ```
