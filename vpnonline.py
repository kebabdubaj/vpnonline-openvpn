#!/usr/bin/env python3

import collections
import io
import multiprocessing
import os
import os.path
import re
import shutil
import signal
import subprocess
import sys
import urllib.request
import zipfile


try:
    import colorama; colorama.init()
    HIGHLIGHT_STYLE, HIGHLIST_RESET = colorama.Fore.RED, colorama.Fore.RESET

except:
    HIGHLIGHT_STYLE, HIGHLIST_RESET = '[', ']'


def current_user():
    return os.environ['SUDO_USER'] if 'SUDO_USER' in os.environ else os.environ['USER']

def has_sudo():
    return 'SUDO_UID' in os.environ


CONFIGURATION_DIRECTORY_PATH = os.path.join(os.path.expanduser('~' + current_user()), '.vpnonline')
CONFIGURATION_DIRECTORY_PERMISSIONS = 0o600

DEFINITIONS_URL = 'https://vpnonline.pl/download/OpenVPN_config_Linux.zip'
DEFINITION_EXTENSIONS = {'.ovpn'}

DEFINITIONS_DIRECTORY_NAME = 'definitions'
DEFINITIONS_DIRECTORY_PATH = os.path.join(CONFIGURATION_DIRECTORY_PATH, DEFINITIONS_DIRECTORY_NAME)

# https://github.com/kylemanna/docker-openvpn/issues/330#issuecomment-346697599
BROKEN_DEFINITION_OPTIONS = [
    'block-outside-dns'
]

CREDENTIALS_FILE_NAME = 'credentials.txt'
CREDENTIALS_FILE_PATH = os.path.join(CONFIGURATION_DIRECTORY_PATH, CREDENTIALS_FILE_NAME)


def list_files(directory_path, extensions):
    for root_path, _, file_paths in os.walk(directory_path):
        for file_path in file_paths:
            _, file_extension = os.path.splitext(file_path)

            if file_extension in extensions:
                yield root_path, file_path

def clear_directory(directory_path):
    for path in os.listdir(directory_path):
        if os.path.isdir(path):
            shutil.rmtree(path)

        if os.path.isfile(path):
            os.remove(path)

def or_pattern(expressions):
    return '|'.join(map(str.lower, expressions))

def and_pattern(expressions):
    return ''.join(f'(?=.*{expression})' for expression in map(str.lower, expressions))

def highlight_expressions(text, expressions, style, reset):
    regex = re.compile(or_pattern(expressions))
    text_parts = []
    last_stop = 0

    for start, stop in map(re.Match.span, regex.finditer(text.lower())):
        text_parts.append(text[last_stop:start])
        text_parts.append(style)
        
        text_parts.append(text[start:stop])
        text_parts.append(reset)

        last_stop = stop

    text_parts.append(text[last_stop:])

    return ''.join(text_parts)


def write_credentials(credentials_path, user_name, user_pass):
    with open(credentials_path, 'w') as ofs:
        ofs.write(user_name + os.linesep)
        ofs.write(user_pass)

    os.chmod(credentials_path, CONFIGURATION_DIRECTORY_PERMISSIONS)    

def fix_broken_definition(file_path, broken_options):
    with open(file_path, 'r') as ifs:
        definition_lines = ifs.readlines()

        fixed_definition_lines = []

        for definition_line in definition_lines:
            if all(broken_option not in definition_line for broken_option in broken_options):
                fixed_definition_lines.append(definition_line)

    if len(fixed_definition_lines) < len(definition_lines):
        with open(file_path, 'w') as ofs:
            ofs.writelines(fixed_definition_lines)

def fix_broken_definitions(start_path, extensions, broken_options):
    for root_path, file_path in list_files(start_path, extensions):
        definition_path = os.path.join(root_path, file_path)
        fix_broken_definition(definition_path, broken_options)

def fetch_definitions(definitions_url):
    request = urllib.request.Request(url=definitions_url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    return io.BytesIO(response.read())

def extract_definitions(definitions_file, definitions_directory, extensions, skip_subtrees=True):       
    with zipfile.ZipFile(definitions_file, 'r') as zip_ifs:
        for zip_file in zip_ifs.filelist:
            if skip_subtrees:
                zip_file.filename = os.path.basename(zip_file.filename)
            _, zip_file_extension = os.path.splitext(zip_file.filename)

            if zip_file_extension in extensions:
                zip_ifs.extract(zip_file, definitions_directory)

def index_definitions(definitions_directory, extensions):
    definition_paths = sorted(list_files(definitions_directory, extensions))
    return collections.OrderedDict(enumerate(definition_paths, 1))       
                
def filter_definitions(indexed_definitions, expressions):
    regex = re.compile(and_pattern(expressions))
    return collections.OrderedDict(
        (i, (x, y))
        for i, (x, y) in indexed_definitions.items()
        if regex.match(y.lower()))

def highlight_definitions(indexed_definitions, expressions):
    return collections.OrderedDict(
        (i, (x, highlight_expressions(y, expressions, HIGHLIGHT_STYLE, HIGHLIST_RESET)))
        for i, (x, y) in indexed_definitions.items())


def prepare_definitions():
    definitions_file = fetch_definitions(DEFINITIONS_URL)

    extract_definitions(definitions_file, DEFINITIONS_DIRECTORY_PATH, DEFINITION_EXTENSIONS)
    fix_broken_definitions(DEFINITIONS_DIRECTORY_PATH, DEFINITION_EXTENSIONS, BROKEN_DEFINITION_OPTIONS) 

def print_definitions(indexed_definitions):
    for i, (_, file_path) in indexed_definitions.items():
        print(f'{i:<3} {file_path}')


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='A script for connecting to VPNOnline servers via OpenVPN')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reset-definitions', action='store_true', help='removes fetched definitions')
    group.add_argument('--reset-credentials', action='store_true', help='removes saved credentials')
    group.add_argument('--reset', action='store_true', help='removes definitions and credentials, (removes ~/.vpnonline)')
    
    group.add_argument('--list', action='store_true', help='print enumerated list of available definitions')
    group.add_argument('--search', nargs='+', help='print enumerated list of definitions containing all provided keywords')
    group.add_argument('--connect', type=int, help='establish connection described by nth-definition')

    parser.add_argument('--detach', action='store_true', help='don\'t capture output nor wait for connection subprocess to finish')

    args = parser.parse_args()

    if args.detach and not args.connect:
        parser.error('%s requires %s' % ('--detach', '--connect'))

    if not has_sudo():
        print('%s has to be run with sudo' % __file__); exit()
    
    if args.reset_definitions:
        clear_directory(DEFINITIONS_DIRECTORY_PATH); exit()

    if args.reset_credentials:
        os.remove(CREDENTIALS_FILE_PATH); exit()   

    if args.reset:
        shutil.rmtree(CONFIGURATION_DIRECTORY_PATH); exit()     

    if not os.path.exists(CONFIGURATION_DIRECTORY_PATH):
        os.mkdir(CONFIGURATION_DIRECTORY_PATH)
    
    if not os.path.exists(DEFINITIONS_DIRECTORY_PATH):
        os.mkdir(DEFINITIONS_DIRECTORY_PATH)
        prepare_definitions()

    if not os.path.exists(CREDENTIALS_FILE_PATH):
        user_name = input('user-name: ')
        user_pass = input('user-pass: ')

        write_credentials(CREDENTIALS_FILE_PATH, user_name, user_pass)
    
    indexed_definitions = index_definitions(DEFINITIONS_DIRECTORY_PATH, DEFINITION_EXTENSIONS)

    if args.list:
        print_definitions(indexed_definitions)

    if args.search:
        filtered_indexed_definitions = filter_definitions(indexed_definitions, args.search)
        highlighted_indexed_definitions = highlight_definitions(filtered_indexed_definitions, args.search)
        
        print_definitions(highlighted_indexed_definitions)

    if args.connect:
        try:
            definition_path = os.path.join(*indexed_definitions[args.connect])

            process_kwargs = {'text': True}
            
            if args.detach:
                process_kwargs.update({'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL})

            process = subprocess.Popen(['openvpn', '--config', definition_path, '--auth-user-pass', CREDENTIALS_FILE_PATH], **process_kwargs)

            if not args.detach:
                return_code = process.wait()
                exit(return_code)    

        except KeyError:
            print('no such connection: %s' % args.connect); exit()
