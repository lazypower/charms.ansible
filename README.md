# charms.ansible

Do you have existing ansible playbooks you want to use in Juju Charms? This
library works in tandem with `layer:ansible` to deliver a consistent Ansible with
juju experience. Just bring your playbooks and operational knowledge.

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
