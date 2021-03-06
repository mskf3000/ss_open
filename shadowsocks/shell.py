#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2015 clowwindy
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function,  with_statement

import os
import json
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import getopt
sys.path.insert(0, os.path.split(os.path.split(os.path.realpath(sys.argv[0]))[0])[0])
from shadowsocks.common import to_bytes, to_str, IPNetwork
from shadowsocks import encrypt,common
import random,time
#logging = sys.modules['logging']
import logging

verbose = 0


def check_python():
    info = sys.version_info
    if info[0] == 2 and not info[1] >= 6:
        print('Python 2.6+ required')
        sys.exit(1)
    elif info[0] == 3 and not info[1] >= 3:
        print('Python 3.3+ required')
        sys.exit(1)
    elif info[0] not in [2, 3]:
        print('Python version not supported')
        sys.exit(1)


def print_exception(e):
    global verbose
    logging.exception("%s" % to_str(e.message))
    if verbose > 0:
        import traceback
        traceback.print_exc()


def print_shadowsocks():
    version = ''
    try:
        import pkg_resources
        version = pkg_resources.get_distribution('shadowsocks').version
    except Exception:
        pass
    print('Shadowsocks %s' % version)


def find_config():
    config_path = 'config.json'
    if os.path.exists(config_path):
        return config_path
    config_path = os.path.join(os.path.dirname(__file__), '../', 'config.json')
    if os.path.exists(config_path):
        return config_path
    return None


def check_config(config, is_local):
    if config.get('daemon', None) == 'stop':
        # no need to specify configuration for daemon stop
        return

    if is_local and not config.get('password', None) and not config.get('port_password',None):
        logging.error('password or port_password not specified')
        print_help(is_local)
        sys.exit(2)

    if not is_local and not config.get('password', None)  and not config.get('port_password', None):
        logging.error('password or port_password not specified')
        print_help(is_local)
        sys.exit(2)

    if config.has_key('port_password') and len(config['port_password']) != 0:
        config['server_port'] = int(random.choice(config['port_password'].items())[0])
        config['password'] = common.to_str(config['port_password']["%s" % config['server_port']])
    else:
        if config.has_key("password") and config.has_key("server_port"):
            if type(config['server_port']) == list and len(config['server_port']) != 0:
                config['server_port'] = random.choice(config.get('server_port', 1990))
            elif type(config['server_port']) == str and config['server_port'] != "":
                config['server_port'] == int(common.to_str(config.get('server_port',1990)))
            elif type(config['server_port']) == int and config['server_port'] <= 65530:
                config['server_port'] = config['server_port']
            else:
                print("Sorry..config error please check config.json again")
                sys.exit(1)
            if config['password'] == "":
                print("Sorry..config error please check config.json again [password is empty]")
                sys.exit(1)
        else:
            print("Sorry..config error please check config.json again [At lease give me password and server_port]")
            sys.exit(1)

    if 'local_port' in config:
        config['local_port'] = int(config['local_port'])

    if 'server_port' in config and type(config['server_port']) != list:
        config['server_port'] = int(config['server_port'])

    if config.get('local_address', '') in [b'0.0.0.0']:
        logging.warn('warning: local set to listen on 0.0.0.0, it\'s not safe')
    if config.get('server', '') in ['127.0.0.1', 'localhost']:
        logging.warn('warning: server set to listen on %s:%s, are you sure?' % (to_str(config['server']), config['server_port']))
    if (config.get('method', '') or '').lower() == 'table':
        logging.warn('warning: table is not safe; please use a safer cipher, like AES-256-CFB')
    if (config.get('method', '') or '').lower() == 'rc4':
        logging.warn('warning: RC4 is not safe; please use a safer cipher,like AES-256-CFB')
    if config.get('timeout', 300) < 100:
        logging.warn('warning: your timeout %d seems too short' % int(config.get('timeout')))
    if config.get('timeout', 300) > 600:
        logging.warn('warning: your timeout %d seems too long' % int(config.get('timeout')))
    if config.get('password') in [b'mypassword']:
        logging.error('DON\'T USE DEFAULT PASSWORD! Please change it in your config.json!')
        sys.exit(1)
    if config['log'].has_key('log_enable') is False:
        config['log'] = {}
        config['log']['log_enable'] = False
    if config['log'].has_key('log_path') is False:
        config['log']['log_path'] = "%s" % os.path.expanduser("~/ss.log")
    if config['forbid'].has_key('site') is False:
        config['forbid'] = {}
        config['forbid']['site'] = []
    if config['forbid'].has_key('port') is False:
        config['forbid']['port'] = []
    if config.get('user', None) is not None:
        if os.name != 'posix':
            logging.error('user can be used only on Unix')
            sys.exit(1)
    encrypt.try_cipher(config['password'], config['method'])


def get_config(is_local):
    global verbose

    if is_local:
        shortopts = 'hd:s:b:p:k:l:m:c:t:vq'
        longopts = ['help', 'fast-open', 'pid-file=', 'log-file=', 'user=', 'version']
    else:
        shortopts = 'hd:s:p:k:m:c:t:vq'
        longopts = ['help', 'fast-open', 'pid-file=', 'log-file=', 'workers=', 'forbidden-ip=', 'user=', 'manager-address=', 'version']
    try:
        config_path = find_config()
        optlist, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
        for key, value in optlist:
            if key == '-c':
                config_path = value

        if config_path:
            logging.info('loading config from %s' % config_path)
            with open(config_path, 'rb') as f:
                try:
                    #config = json.loads(f.read())
                    config = json.loads(f.read().decode('utf8'),object_hook=_decode_dict)
                except ValueError as e:
                    logging.error('found an error in config.json: [%s] .. Please make sure path like: [C:\\ss\\ss.log] on win platform' % str(e))
                    sys.exit(1)
        else:
            config = {}

        v_count = 0
        for key, value in optlist:
            if key == '-p':
                config['server_port'] = int(value)
            elif key == '-k':
                config['password'] = to_bytes(value)
            elif key == '-l':
                config['local_port'] = int(value)
            elif key == '-s':
                config['server'] = to_str(value)
            elif key == '-m':
                config['method'] = to_str(value)
            elif key == '-b':
                config['local_address'] = to_str(value)
            elif key == '-v':
                v_count += 1
                # '-vv' turns on more verbose mode
                config['verbose'] = v_count
            elif key == '-t':
                config['timeout'] = int(value)
            elif key == '--fast-open':
                config['fast_open'] = True
            elif key == '--workers':
                config['workers'] = int(value)
            elif key == '--user':
                config['user'] = to_str(value)
            elif key == '--forbidden-ip':
                config['forbidden_ip'] = to_str(value).split(',')
            elif key in ('-h', '--help'):
                if is_local:
                    print_local_help()
                else:
                    print_server_help()
                sys.exit(0)
            elif key == '--version':
                print_shadowsocks()
                sys.exit(0)
            elif key == '--manager-address':
                config['manager_address'] = value
            elif key == '-d':
                config['daemon'] = to_str(value)
            elif key == '--pid-file':
                config['pid-file'] = to_str(value)
            elif key == '--log-file':
                config['log-file'] = to_str(value)
            elif key == '-q':
                v_count -= 1
                config['verbose'] = v_count
    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print_help(is_local)
        sys.exit(2)

    if not config:
        logging.error('config not specified')
        print_help(is_local)
        sys.exit(2)

    config['password'] = to_bytes(config.get('password', b''))
    config['server_port'] = to_bytes(config.get('server_port', b''))
    config['method'] = to_str(config.get('method', 'aes-256-cfb'))
    config['port_password'] = config.get('port_password', None)
    config['timeout'] = int(config.get('timeout', 300))
    config['fast_open'] = config.get('fast_open', False)
    config['workers'] = config.get('workers', 1)
    if "ss_no_change" in str(os.getcwd()):
        ak = "ss_no_change"
        log_ak = "ss_no_change"
    elif "ss_hub" in str(os.getcwd()):
        ak = "ss_hub"
        log_ak = "ss_hub"
    else:
        ak = "ss"
        log_ak = "ss"
    config['pid-file'] = config.get('pid-file', "/var/run/shadowsocks_%s.pid" % ak)
    config['log-file'] = config.get('log-file', "/var/log/shadowsocks_%s.log" % log_ak)
    config['verbose'] = config.get('verbose', False)
    config['local_address'] = to_str(config.get('local_address', '127.0.0.1'))
    config['local_port'] = config.get('local_port', 1080)
    config['log'] = config.get('log',{'log_enable':'','log_path':''})
    config['forbid'] = config.get('forbid',{'site':[''],'port':['']})
    if is_local:
        if config.get('server', None) is None:
            logging.error('server addr not specified')
            print_local_help()
            sys.exit(2)
        else:
            if type(config["server"]) == list and config['server']:
                config["server"] = to_str(random.choice(config["server"])).strip()
            elif type(config['server']) is list and len(config['server']) == 0:
                logging.error("You must write your VPS ips in config['server']")
                sys.exit(2)
            elif type(config['server']) is str and len(config['server']) == 0:
                logging.error("You must write your VPS ips in config['server']")
                sys.exit(2)
            else:
                config['server'] = to_str(config['server'])
    else:
        config['server'] = to_str(config.get('server', '0.0.0.0'))
        try:
            config['forbidden_ip'] = IPNetwork(config.get('forbidden_ip', '127.0.0.0/8,::1/128'),config)
        except Exception as e:
            logging.error(e)
            sys.exit(2)

    logging.getLogger('').handlers = []
    if config['verbose'] >= 2:
        level = logging.NOTSET
    elif config['verbose'] == 1:
        level = logging.DEBUG
    elif config['verbose'] == -1:
        level = logging.WARN
    elif config['verbose'] <= -2:
        level = logging.ERROR
    else:
        level = logging.INFO
    verbose = config['verbose']
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    check_config(config, is_local)

    return config


def print_help(is_local):
    if is_local:
        print_local_help()
    else:
        print_server_help()


def print_local_help():
    print('''usage: sslocal [OPTION]...
A fast tunnel proxy that helps you bypass firewalls.

You can supply configurations via either config file or command line arguments.

Proxy options:
  -c CONFIG              path to config file
  -s SERVER_ADDR         server address
  -p SERVER_PORT         server port, default: 8388
  -b LOCAL_ADDR          local binding address, default: 127.0.0.1
  -l LOCAL_PORT          local port, default: 1080
  -k PASSWORD            password
  -m METHOD              encryption method, default: aes-256-cfb
  -t TIMEOUT             timeout in seconds, default: 300
  --fast-open            use TCP_FASTOPEN, requires Linux 3.7+

General options:
  -h, --help             show this help message and exit
  -d start/stop/restart  daemon mode
  --pid-file PID_FILE    pid file for daemon mode
  --log-file LOG_FILE    log file for daemon mode
  --user USER            username to run as
  -v, -vv                verbose mode
  -q, -qq                quiet mode, only show warnings/errors
  --version              show version information

Online help: <https://github.com/shadowsocks/shadowsocks>
''')


def print_server_help():
    print('''usage: ssserver [OPTION]...
A fast tunnel proxy that helps you bypass firewalls.

You can supply configurations via either config file or command line arguments.

Proxy options:
  -c CONFIG              path to config file
  -s SERVER_ADDR         server address, default: 0.0.0.0
  -p SERVER_PORT         server port, default: 8388
  -k PASSWORD            password
  -m METHOD              encryption method, default: aes-256-cfb
  -t TIMEOUT             timeout in seconds, default: 300
  --fast-open            use TCP_FASTOPEN, requires Linux 3.7+
  --workers WORKERS      number of workers, available on Unix/Linux
  --forbidden-ip IPLIST  comma seperated IP list forbidden to connect

General options:
  -h, --help             show this help message and exit
  -d start/stop/restart  daemon mode
  --pid-file PID_FILE    pid file for daemon mode
  --log-file LOG_FILE    log file for daemon mode
  --user USER            username to run as
  -v, -vv                verbose mode
  -q, -qq                quiet mode, only show warnings/errors
  --manager-address ADDR optional server manager UDP address, see wiki
  --version              show version information

Online help: <https://github.com/shadowsocks/shadowsocks>
''')


def _decode_list(data):
    rv = []
    for item in data:
        if hasattr(item, 'encode'):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.items():
        if hasattr(value, 'encode'):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        if hasattr(key,"encode"):
            ke = key.encode("utf-8")
        rv[key] = value
    return rv
