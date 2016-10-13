#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

DOCUMENTATION = '''
---
module: nxos_acl
version_added: "2.2"
short_description: Manages access list entries for ACLs.
description:
    - Manages access list entries for ACLs.
extends_documentation_fragment: nxos
author:
    - Jason Edelman (@jedelman8)
    - Gabriele Gerbino (@GGabriele)
notes:
    - I(state)=absent removes the ACE if it exists
    - I(state)=delete_acl deleted the ACL if it exists
    - for idempotency, use port numbers for the src/dest port
      params like I(src_port1) and names for the well defined protocols
      for the I(proto) param.
    - while this module is idempotent in that if the ace as presented in the
      task is identical to the one on the switch, no changes will be made. If
      there is any difference, what is in Ansible will be pushed (configured
      options will be overridden).  This is to improve security, but at the
      same time remember an ACE is removed, then re-added, so if there is a
      change, the new ACE will be exacty what params you are sending to the
      module.
options:
    seq:
        description:
            - sequence number of the entry (ACE)
        required: false
        default: null
    name:
        description:
            - Case sensitive name of the access list (ACL)
        required: true
    action:
        description:
            - action of the ACE
        required: false
        default: null
        choices: ['permit', 'deny', 'remark']
    remark:
        description:
            - If action is set to remark, this is the description
        required: false
        default: null
    proto:
        description:
            - port number or protocol (as supported by the switch)
        required: false
        default: null
    src:
        description:
            - src ip and mask using IP/MASK notation and supports keyword 'any'
        required: false
        default: null
    src_port_op:
        description:
            - src port operands such as eq, neq, gt, lt, range
        required: false
        default: null
        choices: ['any', 'eq', 'gt', 'lt', 'neq', 'range']
    src_port1:
        description:
            - port/protocol and also first (lower) port when using range
              operand
        required: false
        default: null
    src_port2:
        description:
            - second (end) port when using range operand
        required: false
        default: null
    dest:
        description:
            - dest ip and mask using IP/MASK notation and supports the
              keyword 'any'
        required: false
        default: null
    dest_port_op:
        description:
            - dest port operands such as eq, neq, gt, lt, range
        required: false
        default: null
        choices: ['any', 'eq', 'gt', 'lt', 'neq', 'range']
    dest_port1:
        description:
            - port/protocol and also first (lower) port when using range
              operand
        required: false
        default: null
    dest_port2:
        description:
            - second (end) port when using range operand
        required: false
        default: null
    log:
        description:
            - Log matches against this entry
        required: false
        default: null
        choices: ['enable']
    urg:
        description:
            - Match on the URG bit
        required: false
        default: null
        choices: ['enable']
    ack:
        description:
            - Match on the ACK bit
        required: false
        default: null
        choices: ['enable']
    psh:
        description:
            - Match on the PSH bit
        required: false
        default: null
        choices: ['enable']
    rst:
        description:
            - Match on the RST bit
        required: false
        default: null
        choices: ['enable']
    syn:
        description:
            - Match on the SYN bit
        required: false
        default: null
        choices: ['enable']
    fin:
        description:
            - Match on the FIN bit
        required: false
        default: null
        choices: ['enable']
    established:
        description:
            - Match established connections
        required: false
        default: null
        choices: ['enable']
    fragments:
        description:
            - Check non-initial fragments
        required: false
        default: null
        choices: ['enable']
    time-range:
        description:
            - Name of time-range to apply
        required: false
        default: null
    precedence:
        description:
            - Match packets with given precedence
        required: false
        default: null
        choices: ['critical', 'flash', 'flash-override', 'immediate',
                  'internet', 'network', 'priority', 'routine']
    dscp:
        description:
            - Match packets with given dscp value
        required: false
        default: null
        choices: ['af11, 'af12, 'af13, 'af21', 'af22', 'af23','af31','af32',
                  'af33', 'af41', 'af42', 'af43', 'cs1', 'cs2', 'cs3', 'cs4',
                  'cs5', 'cs6', 'cs7', 'default', 'ef']
    state:
        description:
            - Specify desired state of the resource
        required: false
        default: present
        choices: ['present','absent','delete_acl']
'''

EXAMPLES = '''

# configure ACL ANSIBLE
- nxos_acl:
    name: ANSIBLE
    seq: 10
    action: permit
    proto: tcp
    src: 1.1.1.1/24
    dest: any
    state: present
    provider: "{{ nxos_provider }}"
'''

RETURN = '''
proposed:
    description: k/v pairs of parameters passed into module.
    returned: always
    type: dict
    sample: {"action": "permit", "dest": "any", "name": "ANSIBLE",
            "proto": "tcp", "seq": "10", "src": "1.1.1.1/24"}
existing:
    description: k/v pairs of existing ACL entries.
    type: dict
    sample: {}
end_state:
    description: k/v pairs of ACL entries after module execution.
    returned: always
    type: dict
    sample: {"action": "permit", "dest": "any", "name": "ANSIBLE",
            "proto": "tcp", "seq": "10", "src": "1.1.1.1/24"}
updates:
    description: commands sent to the device
    returned: always
    type: list
    sample: ["ip access-list ANSIBLE", "10 permit tcp 1.1.1.1/24 any"]
changed:
    description: check to see if a change was made on the device
    returned: always
    type: boolean
    sample: true
'''


# COMMON CODE FOR MIGRATION

import re
import time
import collections
import itertools
import shlex
import json

from ansible.module_utils.basic import AnsibleModule, env_fallback, get_exception
from ansible.module_utils.basic import BOOLEANS_TRUE, BOOLEANS_FALSE
from ansible.module_utils.shell import Shell, ShellError, HAS_PARAMIKO
from ansible.module_utils.netcfg import parse
from ansible.module_utils.urls import fetch_url


DEFAULT_COMMENT_TOKENS = ['#', '!']

class ConfigLine(object):

    def __init__(self, text):
        self.text = text
        self.children = list()
        self.parents = list()
        self.raw = None

    @property
    def line(self):
        line = ['set']
        line.extend([p.text for p in self.parents])
        line.append(self.text)
        return ' '.join(line)

    def __str__(self):
        return self.raw

    def __eq__(self, other):
        if self.text == other.text:
            return self.parents == other.parents

    def __ne__(self, other):
        return not self.__eq__(other)

def ignore_line(text, tokens=None):
    for item in (tokens or DEFAULT_COMMENT_TOKENS):
        if text.startswith(item):
            return True

def get_next(iterable):
    item, next_item = itertools.tee(iterable, 2)
    next_item = itertools.islice(next_item, 1, None)
    return itertools.izip_longest(item, next_item)

def parse(lines, indent, comment_tokens=None):
    toplevel = re.compile(r'\S')
    childline = re.compile(r'^\s*(.+)$')

    ancestors = list()
    config = list()

    for line in str(lines).split('\n'):
        text = str(re.sub(r'([{};])', '', line)).strip()

        cfg = ConfigLine(text)
        cfg.raw = line

        if not text or ignore_line(text, comment_tokens):
            continue

        # handle top level commands
        if toplevel.match(line):
            ancestors = [cfg]

        # handle sub level commands
        else:
            match = childline.match(line)
            line_indent = match.start(1)
            level = int(line_indent / indent)
            parent_level = level - 1

            cfg.parents = ancestors[:level]

            if level > len(ancestors):
                config.append(cfg)
                continue

            for i in range(level, len(ancestors)):
                ancestors.pop()

            ancestors.append(cfg)
            ancestors[parent_level].children.append(cfg)

        config.append(cfg)

    return config


class CustomNetworkConfig(object):

    def __init__(self, indent=None, contents=None, device_os=None):
        self.indent = indent or 1
        self._config = list()
        self._device_os = device_os

        if contents:
            self.load(contents)

    @property
    def items(self):
        return self._config

    @property
    def lines(self):
        lines = list()
        for item, next_item in get_next(self.items):
            if next_item is None:
                lines.append(item.line)
            elif not next_item.line.startswith(item.line):
                lines.append(item.line)
        return lines

    def __str__(self):
        text = ''
        for item in self.items:
            if not item.parents:
                expand = self.get_section(item.text)
                text += '%s\n' % self.get_section(item.text)
        return str(text).strip()

    def load(self, contents):
        self._config = parse(contents, indent=self.indent)

    def load_from_file(self, filename):
        self.load(open(filename).read())

    def get(self, path):
        if isinstance(path, basestring):
            path = [path]
        for item in self._config:
            if item.text == path[-1]:
                parents = [p.text for p in item.parents]
                if parents == path[:-1]:
                    return item

    def search(self, regexp, path=None):
        regex = re.compile(r'^%s' % regexp, re.M)

        if path:
            parent = self.get(path)
            if not parent or not parent.children:
                return
            children = [c.text for c in parent.children]
            data = '\n'.join(children)
        else:
            data = str(self)

        match = regex.search(data)
        if match:
            if match.groups():
                values = match.groupdict().values()
                groups = list(set(match.groups()).difference(values))
                return (groups, match.groupdict())
            else:
                return match.group()

    def findall(self, regexp):
        regexp = r'%s' % regexp
        return re.findall(regexp, str(self))

    def expand(self, obj, items):
        block = [item.raw for item in obj.parents]
        block.append(obj.raw)

        current_level = items
        for b in block:
            if b not in current_level:
                current_level[b] = collections.OrderedDict()
            current_level = current_level[b]
        for c in obj.children:
            if c.raw not in current_level:
                current_level[c.raw] = collections.OrderedDict()

    def to_lines(self, section):
        lines = list()
        for entry in section[1:]:
            line = ['set']
            line.extend([p.text for p in entry.parents])
            line.append(entry.text)
            lines.append(' '.join(line))
        return lines

    def to_block(self, section):
        return '\n'.join([item.raw for item in section])

    def get_section(self, path):
        try:
            section = self.get_section_objects(path)
            if self._device_os == 'junos':
                return self.to_lines(section)
            return self.to_block(section)
        except ValueError:
            return list()

    def get_section_objects(self, path):
        if not isinstance(path, list):
            path = [path]
        obj = self.get_object(path)
        if not obj:
            raise ValueError('path does not exist in config')
        return self.expand_section(obj)

    def expand_section(self, configobj, S=None):
        if S is None:
            S = list()
        S.append(configobj)
        for child in configobj.children:
            if child in S:
                continue
            self.expand_section(child, S)
        return S

    def flatten(self, data, obj=None):
        if obj is None:
            obj = list()
        for k, v in data.items():
            obj.append(k)
            self.flatten(v, obj)
        return obj

    def get_object(self, path):
        for item in self.items:
            if item.text == path[-1]:
                parents = [p.text for p in item.parents]
                if parents == path[:-1]:
                    return item

    def get_children(self, path):
        obj = self.get_object(path)
        if obj:
            return obj.children

    def difference(self, other, path=None, match='line', replace='line'):
        updates = list()

        config = self.items
        if path:
            config = self.get_children(path) or list()

        if match == 'line':
            for item in config:
                if item not in other.items:
                    updates.append(item)

        elif match == 'strict':
            if path:
                current = other.get_children(path) or list()
            else:
                current = other.items

            for index, item in enumerate(config):
                try:
                    if item != current[index]:
                        updates.append(item)
                except IndexError:
                    updates.append(item)

        elif match == 'exact':
            if path:
                current = other.get_children(path) or list()
            else:
                current = other.items

            if len(current) != len(config):
                updates.extend(config)
            else:
                for ours, theirs in itertools.izip(config, current):
                    if ours != theirs:
                        updates.extend(config)
                        break

        if self._device_os == 'junos':
            return updates

        diffs = collections.OrderedDict()
        for update in updates:
            if replace == 'block' and update.parents:
                update = update.parents[-1]
            self.expand(update, diffs)

        return self.flatten(diffs)

    def replace(self, replace, text=None, regex=None, parents=None,
            add_if_missing=False, ignore_whitespace=False):
        match = None

        parents = parents or list()
        if text is None and regex is None:
            raise ValueError('missing required arguments')

        if not regex:
            regex = ['^%s$' % text]

        patterns = [re.compile(r, re.I) for r in to_list(regex)]

        for item in self.items:
            for regexp in patterns:
                if ignore_whitespace is True:
                    string = item.text
                else:
                    string = item.raw
                if regexp.search(item.text):
                    if item.text != replace:
                        if parents == [p.text for p in item.parents]:
                            match = item
                            break

        if match:
            match.text = replace
            indent = len(match.raw) - len(match.raw.lstrip())
            match.raw = replace.rjust(len(replace) + indent)

        elif add_if_missing:
            self.add(replace, parents=parents)


    def add(self, lines, parents=None):
        """Adds one or lines of configuration
        """

        ancestors = list()
        offset = 0
        obj = None

        ## global config command
        if not parents:
            for line in to_list(lines):
                item = ConfigLine(line)
                item.raw = line
                if item not in self.items:
                    self.items.append(item)

        else:
            for index, p in enumerate(parents):
                try:
                    i = index + 1
                    obj = self.get_section_objects(parents[:i])[0]
                    ancestors.append(obj)

                except ValueError:
                    # add parent to config
                    offset = index * self.indent
                    obj = ConfigLine(p)
                    obj.raw = p.rjust(len(p) + offset)
                    if ancestors:
                        obj.parents = list(ancestors)
                        ancestors[-1].children.append(obj)
                    self.items.append(obj)
                    ancestors.append(obj)

            # add child objects
            for line in to_list(lines):
                # check if child already exists
                for child in ancestors[-1].children:
                    if child.text == line:
                        break
                else:
                    offset = len(parents) * self.indent
                    item = ConfigLine(line)
                    item.raw = line.rjust(len(line) + offset)
                    item.parents = ancestors
                    ancestors[-1].children.append(item)
                    self.items.append(item)


def argument_spec():
    return dict(
        # config options
        running_config=dict(aliases=['config']),
        save_config=dict(type='bool', default=False, aliases=['save'])
    )
nxos_argument_spec = argument_spec()


NET_PASSWD_RE = re.compile(r"[\r\n]?password: $", re.I)

NET_COMMON_ARGS = dict(
    host=dict(required=True),
    port=dict(type='int'),
    username=dict(fallback=(env_fallback, ['ANSIBLE_NET_USERNAME'])),
    password=dict(no_log=True, fallback=(env_fallback, ['ANSIBLE_NET_PASSWORD'])),
    ssh_keyfile=dict(fallback=(env_fallback, ['ANSIBLE_NET_SSH_KEYFILE']), type='path'),
    transport=dict(default='cli', choices=['cli', 'nxapi']),
    use_ssl=dict(default=False, type='bool'),
    validate_certs=dict(default=True, type='bool'),
    provider=dict(type='dict'),
    timeout=dict(default=10, type='int')
)

NXAPI_COMMAND_TYPES = ['cli_show', 'cli_show_ascii', 'cli_conf', 'bash']

NXAPI_ENCODINGS = ['json', 'xml']

CLI_PROMPTS_RE = [
    re.compile(r'[\r\n]?[a-zA-Z]{1}[a-zA-Z0-9-]*[>|#|%](?:\s*)$'),
    re.compile(r'[\r\n]?[a-zA-Z]{1}[a-zA-Z0-9-]*\(.+\)#(?:\s*)$')
]

CLI_ERRORS_RE = [
    re.compile(r"% ?Error"),
    re.compile(r"^% \w+", re.M),
    re.compile(r"% ?Bad secret"),
    re.compile(r"invalid input", re.I),
    re.compile(r"(?:incomplete|ambiguous) command", re.I),
    re.compile(r"connection timed out", re.I),
    re.compile(r"[^\r\n]+ not found", re.I),
    re.compile(r"'[^']' +returned error code: ?\d+"),
    re.compile(r"syntax error"),
    re.compile(r"unknown command")
]


def to_list(val):
    if isinstance(val, (list, tuple)):
        return list(val)
    elif val is not None:
        return [val]
    else:
        return list()


class Nxapi(object):

    def __init__(self, module):
        self.module = module

        # sets the module_utils/urls.py req parameters
        self.module.params['url_username'] = module.params['username']
        self.module.params['url_password'] = module.params['password']

        self.url = None
        self._nxapi_auth = None

    def _get_body(self, commands, command_type, encoding, version='1.0', chunk='0', sid=None):
        """Encodes a NXAPI JSON request message
        """
        if isinstance(commands, (list, set, tuple)):
            commands = ' ;'.join(commands)

        if encoding not in NXAPI_ENCODINGS:
            msg = 'invalid encoding, received %s, exceped one of %s' % \
                    (encoding, ','.join(NXAPI_ENCODINGS))
            self.module_fail_json(msg=msg)

        msg = {
            'version': version,
            'type': command_type,
            'chunk': chunk,
            'sid': sid,
            'input': commands,
            'output_format': encoding
        }
        return dict(ins_api=msg)

    def connect(self):
        host = self.module.params['host']
        port = self.module.params['port']

        if self.module.params['use_ssl']:
            proto = 'https'
            if not port:
                port = 443
        else:
            proto = 'http'
            if not port:
                port = 80

        self.url = '%s://%s:%s/ins' % (proto, host, port)

    def send(self, commands, command_type='cli_show_ascii', encoding='json'):
        """Send commands to the device.
        """
        clist = to_list(commands)

        if command_type not in NXAPI_COMMAND_TYPES:
            msg = 'invalid command_type, received %s, exceped one of %s' % \
                    (command_type, ','.join(NXAPI_COMMAND_TYPES))
            self.module_fail_json(msg=msg)

        data = self._get_body(clist, command_type, encoding)
        data = self.module.jsonify(data)

        headers = {'Content-Type': 'application/json'}
        if self._nxapi_auth:
            headers['Cookie'] = self._nxapi_auth

        response, headers = fetch_url(self.module, self.url, data=data,
                headers=headers, method='POST')

        self._nxapi_auth = headers.get('set-cookie')

        if headers['status'] != 200:
            self.module.fail_json(**headers)

        response = self.module.from_json(response.read())
        result = list()

        output = response['ins_api']['outputs']['output']
        for item in to_list(output):
            if item['code'] != '200':
                self.module.fail_json(**item)
            else:
                result.append(item['body'])

        return result


class Cli(object):

    def __init__(self, module):
        self.module = module
        self.shell = None

    def connect(self, **kwargs):
        host = self.module.params['host']
        port = self.module.params['port'] or 22

        username = self.module.params['username']
        password = self.module.params['password']
        timeout = self.module.params['timeout']
        key_filename = self.module.params['ssh_keyfile']

        allow_agent = (key_filename is not None) or (key_filename is None and password is None)

        try:
            self.shell = Shell(kickstart=False, prompts_re=CLI_PROMPTS_RE,
                    errors_re=CLI_ERRORS_RE)
            self.shell.open(host, port=port, username=username,
                    password=password, key_filename=key_filename,
                    allow_agent=allow_agent, timeout=timeout)
        except ShellError:
            e = get_exception()
            msg = 'failed to connect to %s:%s - %s' % (host, port, str(e))
            self.module.fail_json(msg=msg)

    def send(self, commands, encoding='text'):
        try:
            return self.shell.send(commands)
        except ShellError:
            e = get_exception()
            self.module.fail_json(msg=e.message, commands=commands)


class NetworkModule(AnsibleModule):

    def __init__(self, *args, **kwargs):
        super(NetworkModule, self).__init__(*args, **kwargs)
        self.connection = None
        self._config = None
        self._connected = False

    @property
    def connected(self):
        return self._connected

    @property
    def config(self):
        if not self._config:
            self._config = self.get_config()
        return self._config

    def _load_params(self):
        super(NetworkModule, self)._load_params()
        provider = self.params.get('provider') or dict()
        for key, value in provider.items():
            if key in NET_COMMON_ARGS:
                if self.params.get(key) is None and value is not None:
                    self.params[key] = value

    def connect(self):
        cls = globals().get(str(self.params['transport']).capitalize())
        try:
            self.connection = cls(self)
        except TypeError:
            e = get_exception()
            self.fail_json(msg=e.message)

        self.connection.connect()

        if self.params['transport'] == 'cli':
            self.connection.send('terminal length 0')

        self._connected = True

    def configure(self, commands):
        commands = to_list(commands)
        if self.params['transport'] == 'cli':
            return self.configure_cli(commands)
        else:
            return self.execute(commands, command_type='cli_conf')

    def configure_cli(self, commands):
        commands = to_list(commands)
        commands.insert(0, 'configure')
        responses = self.execute(commands)
        responses.pop(0)
        return responses

    def execute(self, commands, **kwargs):
        if not self.connected:
            self.connect()
        return self.connection.send(commands, **kwargs)

    def disconnect(self):
        self.connection.close()
        self._connected = False

    def parse_config(self, cfg):
        return parse(cfg, indent=2)

    def get_config(self):
        cmd = 'show running-config'
        if self.params.get('include_defaults'):
            cmd += ' all'
        response = self.execute(cmd)
        return response[0]


def get_module(**kwargs):
    """Return instance of NetworkModule
    """
    argument_spec = NET_COMMON_ARGS.copy()
    if kwargs.get('argument_spec'):
        argument_spec.update(kwargs['argument_spec'])
    kwargs['argument_spec'] = argument_spec

    module = NetworkModule(**kwargs)

    if module.params['transport'] == 'cli' and not HAS_PARAMIKO:
        module.fail_json(msg='paramiko is required but does not appear to be installed')

    return module


def custom_get_config(module, include_defaults=False):
    config = module.params['running_config']
    if not config:
        cmd = 'show running-config'
        if module.params['include_defaults']:
            cmd += ' all'
        if module.params['transport'] == 'nxapi':
            config = module.execute([cmd], command_type='cli_show_ascii')[0]
        else:
            config = module.execute([cmd])[0]

    return CustomNetworkConfig(indent=2, contents=config)

def load_config(module, candidate):
    config = custom_get_config(module)

    commands = candidate.difference(config)
    commands = [str(c).strip() for c in commands]

    save_config = module.params['save_config']

    result = dict(changed=False)

    if commands:
        if not module.check_mode:
            module.configure(commands)
            if save_config:
                module.config.save_config()

        result['changed'] = True
        result['updates'] = commands

    return result
# END OF COMMON CODE

def get_cli_body_ssh(command, response, module):
    """Get response for when transport=cli.  This is kind of a hack and mainly
    needed because these modules were originally written for NX-API.  And
    not every command supports "| json" when using cli/ssh.  As such, we assume
    if | json returns an XML string, it is a valid command, but that the
    resource doesn't exist yet. Instead, we assume if '^' is found in response,
    it is an invalid command.
    """
    if 'xml' in response[0]:
        body = []
    elif '^' in response[0]:
        body = response
    else:
        try:
            body = [json.loads(response[0])]
        except ValueError:
            module.fail_json(msg='Command does not support JSON output',
                             command=command)
    return body


def execute_show(cmds, module, command_type=None):
    try:
        if command_type:
            response = module.execute(cmds, command_type=command_type)
        else:
            response = module.execute(cmds)
    except ShellError:
        clie = get_exception()
        module.fail_json(msg='Error sending {0}'.format(cmds),
                         error=str(clie))
    except AttributeError:
        try:
            if command_type:
                command_type = command_type_map.get(command_type)
                module.cli.add_commands(cmds, output=command_type)
                response = module.cli.run_commands()
            else:
                module.cli.add_commands(cmds, raw=True)
                response = module.cli.run_commands()
        except ShellError:
            clie = get_exception()
            module.fail_json(msg='Error sending {0}'.format(cmds),
                             error=str(clie))
    return response


def execute_show_command(command, module, command_type='cli_show'):
    if module.params['transport'] == 'cli':
        command += ' | json'
        cmds = [command]
        response = execute_show(cmds, module)
        body = get_cli_body_ssh(command, response, module)
    elif module.params['transport'] == 'nxapi':
        cmds = [command]
        body = execute_show(cmds, module, command_type=command_type)

    return body


def get_acl(module, acl_name, seq_number):
    command = 'show ip access-list'
    new_acl = []
    saveme = {}
    seqs = []
    acl_body = {}

    body = execute_show_command(command, module)[0]
    all_acl_body = body['TABLE_ip_ipv6_mac']['ROW_ip_ipv6_mac']

    for acl in all_acl_body:
        if acl.get('acl_name') == acl_name:
            acl_body = acl

    try:
        acl_entries = acl_body['TABLE_seqno']['ROW_seqno']
        acl_name = acl_body.get('acl_name')
    except KeyError:  # could be raised if no ACEs are configured for an ACL
        return saveme, [{'acl': 'no_entries'}], seqs

    if isinstance(acl_entries, dict):
        acl_entries = [acl_entries]

    for each in acl_entries:
        temp = collections.OrderedDict()
        keep = {}
        temp['name'] = acl_name
        temp['seq'] = str(each.get('seqno'))
        temp['options'] = {}
        remark = each.get('remark')
        if remark:
            temp['remark'] = remark
            temp['action'] = 'remark'
        else:
            temp['action'] = each.get('permitdeny')
            temp['proto'] = each.get('proto', each.get('proto_str', each.get('ip')))
            temp['src'] = each.get('src_any', each.get('src_ip_prefix'))
            temp['src_port_op'] = each.get('src_port_op')
            temp['src_port1'] = each.get('src_port1_num')
            temp['src_port2'] = each.get('src_port2_num')
            temp['dest'] = each.get('dest_any', each.get('dest_ip_prefix'))
            temp['dest_port_op'] = each.get('dest_port_op')
            temp['dest_port1'] = each.get('dest_port1_num')
            temp['dest_port2'] = each.get('dest_port2_num')

            options = collections.OrderedDict()
            options['log'] = each.get('log')
            options['urg'] = each.get('urg')
            options['ack'] = each.get('ack')
            options['psh'] = each.get('psh')
            options['rst'] = each.get('rst')
            options['syn'] = each.get('syn')
            options['fin'] = each.get('fin')
            options['established'] = each.get('established')
            options['dscp'] = each.get('dscp_str')
            options['precedence'] = each.get('precedence_str')
            options['fragments'] = each.get('fragments')
            options['time_range'] = each.get('timerange')

            options_no_null = {}
            for key, value in options.iteritems():
                if value is not None:
                    options_no_null[key] = value

            keep['options'] = options_no_null

        for key, value in temp.iteritems():
            if value:
                keep[key] = value
        # ensure options is always in the dict
        if keep.get('options', 'DNE') == 'DNE':
            keep['options'] = {}

        if keep.get('seq') == seq_number:
            saveme = dict(keep)

        seqs.append(str(keep.get('seq')))
        new_acl.append(keep)

    return saveme, new_acl, seqs


def _acl_operand(operand, srcp1, sprcp2):
    sub_entry = ' ' + operand

    if operand == 'range':
        sub_entry += ' ' + srcp1 + ' ' + sprcp2
    else:
        sub_entry += ' ' + srcp1

    return sub_entry


def config_core_acl(proposed):
    seq = proposed.get('seq')
    action = proposed.get('action')
    remark = proposed.get('remark')
    proto = proposed.get('proto')
    src = proposed.get('src')
    src_port_op = proposed.get('src_port_op')
    src_port1 = proposed.get('src_port1')
    src_port2 = proposed.get('src_port2')

    dest = proposed.get('dest')
    dest_port_op = proposed.get('dest_port_op')
    dest_port1 = proposed.get('dest_port1')
    dest_port2 = proposed.get('dest_port2')

    ace_start_entries = [action, proto, src]
    if not remark:
        ace = seq + ' ' + ' '.join(ace_start_entries)
        if src_port_op:
            ace += _acl_operand(src_port_op, src_port1, src_port2)
        ace += ' ' + dest
        if dest_port_op:
            ace += _acl_operand(dest_port_op, dest_port1, dest_port2)
    else:
        ace = seq + ' remark ' + remark

    return ace


def config_acl_options(options):
    ENABLE_ONLY = ['psh', 'urg', 'log', 'ack', 'syn',
                   'established', 'rst', 'fin', 'fragments',
                   'log']

    OTHER = ['dscp', 'precedence', 'time-range']
    # packet-length is the only option not currently supported

    if options.get('time_range'):
        options['time-range'] = options.get('time_range')
        options.pop('time_range')

    command = ''
    for option, value in options.iteritems():
        if option in ENABLE_ONLY:
            if value == 'enable':
                command += ' ' + option
        elif option in OTHER:
            command += ' ' + option + ' ' + value
    if command:
        command = command.strip()
        return command


def flatten_list(command_lists):
    flat_command_list = []
    for command in command_lists:
        if isinstance(command, list):
            flat_command_list.extend(command)
        else:
            flat_command_list.append(command)
    return flat_command_list


def execute_config_command(commands, module):
    try:
        module.configure(commands)
    except ShellError:
        clie = get_exception()
        module.fail_json(msg='Error sending CLI commands',
                         error=str(clie), commands=commands)
    except AttributeError:
        try:
            commands.insert(0, 'configure')
            module.cli.add_commands(commands, output='config')
            module.cli.run_commands()
        except ShellError:
            clie = get_exception()
            module.fail_json(msg='Error sending CLI commands',
                             error=str(clie), commands=commands)


def main():
    argument_spec = dict(
            seq=dict(required=False, type='str'),
            name=dict(required=True, type='str'),
            action=dict(required=False, choices=['remark', 'permit', 'deny']),
            remark=dict(required=False, type='str'),
            proto=dict(required=False, type='str'),
            src=dict(required=False, type='str'),
            src_port_op=dict(required=False),
            src_port1=dict(required=False, type='str'),
            src_port2=dict(required=False, type='str'),
            dest=dict(required=False, type='str'),
            dest_port_op=dict(required=False),
            dest_port1=dict(required=False, type='str'),
            dest_port2=dict(required=False, type='str'),
            log=dict(required=False, choices=['enable']),
            urg=dict(required=False, choices=['enable']),
            ack=dict(required=False, choices=['enable']),
            psh=dict(required=False, choices=['enable']),
            rst=dict(required=False, choices=['enable']),
            syn=dict(required=False, choices=['enable']),
            fragments=dict(required=False, choices=['enable']),
            fin=dict(required=False, choices=['enable']),
            established=dict(required=False, choices=['enable']),
            time_range=dict(required=False),
            precedence=dict(required=False, choices=['critical', 'flash',
                                                     'flash-override',
                                                     'immediate', 'internet',
                                                     'network', 'priority',
                                                     'routine']),
            dscp=dict(required=False, choices=['af11', 'af12', 'af13', 'af21',
                                               'af22', 'af23', 'af31', 'af32',
                                               'af33', 'af41', 'af42', 'af43',
                                               'cs1', 'cs2', 'cs3', 'cs4',
                                               'cs5', 'cs6', 'cs7', 'default',
                                               'ef']),
            state=dict(choices=['absent', 'present', 'delete_acl'],
                       default='present'),
            protocol=dict(choices=['http', 'https'], default='http'),
            host=dict(required=True),
            username=dict(type='str'),
            password=dict(no_log=True, type='str'),
    )
    argument_spec.update(nxos_argument_spec)
    module = get_module(argument_spec=argument_spec,
                        supports_check_mode=True)

    state = module.params['state']
    action = module.params['action']
    remark = module.params['remark']
    dscp = module.params['dscp']
    precedence = module.params['precedence']
    seq = module.params['seq']
    name = module.params['name']
    seq = module.params['seq']

    if action == 'remark' and not remark:
        module.fail_json(msg='when state is action, remark param is also '
                             'required')

    REQUIRED = ['seq', 'name', 'action', 'proto', 'src', 'dest']
    ABSENT = ['name', 'seq']
    if state == 'present':
        if action and remark and seq:
            pass
        else:
            for each in REQUIRED:
                if module.params[each] is None:
                    module.fail_json(msg="req'd params when state is present:",
                                     params=REQUIRED)
    elif state == 'absent':
        for each in ABSENT:
            if module.params[each] is None:
                module.fail_json(msg='require params when state is absent',
                                 params=ABSENT)
    elif state == 'delete_acl':
        if module.params['name'] is None:
            module.fail_json(msg="param name req'd when state is delete_acl")

    if dscp and precedence:
        module.fail_json(msg='only one of the params dscp/precedence '
                             'are allowed')

    OPTIONS_NAMES = ['log', 'urg', 'ack', 'psh', 'rst', 'syn', 'fin',
                     'established', 'dscp', 'precedence', 'fragments',
                     'time_range']

    CORE = ['seq', 'name', 'action', 'proto', 'src', 'src_port_op',
            'src_port1', 'src_port2', 'dest', 'dest_port_op',
            'dest_port1', 'dest_port2', 'remark']

    proposed_core = dict((param, value) for (param, value) in
                         module.params.iteritems()
                         if param in CORE and value is not None)

    proposed_options = dict((param, value) for (param, value) in
                            module.params.iteritems()
                            if param in OPTIONS_NAMES and value is not None)
    proposed = {}
    proposed.update(proposed_core)
    proposed.update(proposed_options)

    existing_options = {}

    # getting existing existing_core=dict, acl=list, seq=list
    existing_core, acl, seqs = get_acl(module, name, seq)
    if existing_core:
        existing_options = existing_core.get('options')
        existing_core.pop('options')

    end_state = acl
    commands = []
    changed = False
    delta_core = {}
    delta_options = {}

    if not existing_core.get('remark'):
        delta_core = dict(
            set(proposed_core.iteritems()).difference(
                existing_core.iteritems())
            )
        delta_options = dict(
            set(proposed_options.iteritems()).difference(
                existing_options.iteritems())
        )

    if state == 'present':
        if delta_core or delta_options:
            if existing_core:  # if the ace exists already
                commands.append(['no {0}'.format(seq)])
            if delta_options:
                myacl_str = config_core_acl(proposed_core)
                myacl_str += ' ' + config_acl_options(proposed_options)
            else:
                myacl_str = config_core_acl(proposed_core)
            command = [myacl_str]
            commands.append(command)
    elif state == 'absent':
        if existing_core:
            commands.append(['no {0}'.format(seq)])
    elif state == 'delete_acl':
        if acl[0].get('acl') != 'no_entries':
            commands.append(['no ip access-list {0}'.format(name)])

    results = {}
    cmds = []
    if commands:
        preface = []
        if state in ['present', 'absent']:
            preface = ['ip access-list {0}'.format(name)]
            commands.insert(0, preface)

        cmds = flatten_list(commands)
        if module.check_mode:
            module.exit_json(changed=True, commands=cmds)
        else:
            execute_config_command(cmds, module)
            changed = True
            new_existing_core, end_state, seqs = get_acl(module, name, seq)
            if 'configure' in cmds:
                cmds.pop(0)

    results['proposed'] = proposed
    results['existing'] = existing_core
    results['changed'] = changed
    results['updates'] = cmds
    results['end_state'] = end_state

    module.exit_json(**results)


if __name__ == '__main__':
    main()