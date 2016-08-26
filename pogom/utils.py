#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import configargparse
import uuid
import os
import json
from datetime import datetime, timedelta
import logging
import shutil
import platform
import pprint
import time

from . import config

log = logging.getLogger(__name__)


def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string


def verify_config_file_exists(filename):
    fullpath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(fullpath):
        log.info('Could not find %s, copying default', filename)
        shutil.copy2(fullpath + '.example', fullpath)


def memoize(function):
    memo = {}

    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper


@memoize
def get_args():
    # fuck PEP8
    configpath = os.path.join(os.path.dirname(__file__), '../config/config.ini')
    parser = configargparse.ArgParser(default_config_files=[configpath], auto_env_var_prefix='POGOMAP_')
    parser.add_argument('-a', '--auth-service', type=str.lower, action='append',
                        help='Auth Services, either one for all accounts or one per account: ptc or google. Defaults all to ptc.')
    parser.add_argument('-u', '--username', action='append',
                        help='Usernames, one per account.')
    parser.add_argument('-p', '--password', action='append',
                        help='Passwords, either single one for all accounts or one per account.')
    parser.add_argument('--acc-reserve', type=float, default=4, help='The number (or percent) of accounts \
                        to keep in reserve. Reserved accounts are regularily rotated in to reduce \
                        account stress. Defaults to 0 (off)')
    parser.add_argument('-l', '--location', type=parse_unicode,
                        help='Location, can be an address or coordinates')
    parser.add_argument('-j', '--jitter', help='Apply random -9m to +9m jitter to location',
                        action='store_true', default=True)
    parser.add_argument('-st', '--step-limit', help='Steps', type=int,
                        default=12)
    parser.add_argument('-ed', '--encounter-delay',
                        help='Time delay between encounter pokemon in scan threads',
                        type=float, default=10)
    parser.add_argument('-si', '--scan-iv',
                        help='Scan the IV of the pokemon',
                        action='store_true', default=True)
    parser.add_argument('-sd', '--scan-delay',
                        help='Time delay between requests in scan threads',
                        type=float, default=10)
    parser.add_argument('-rd', '--random-delay',
                        help='Random time delay between 0 and RANDOM_DELAY seconds added to SCAN_DELAY after each step',
                        type=int, default=8)
    parser.add_argument('-ld', '--login-delay',
                        help='Time delay between each login attempt',
                        type=float, default=5)
    parser.add_argument('-lr', '--login-retries',
                        help='Number of logins attempts before refreshing a thread',
                        type=int, default=3)
    parser.add_argument('-mf', '--max-failures',
                        help='Maximum number of failures to parse locations before an account will go into a two hour sleep',
                        type=int, default=5)
    parser.add_argument('-msl', '--min-seconds-left',
                        help='Time that must be left on a spawn before considering it too late and skipping it. eg. 600 would skip anything with < 10 minutes remaining. Default 0.',
                        type=int, default=0)
    parser.add_argument('-dc', '--display-in-console',
                        help='Display Found Pokemon in Console',
                        action='store_true', default=False)
    parser.add_argument('-H', '--host', help='Set web server listening host',
                        default='127.0.0.1')
    parser.add_argument('-P', '--port', type=int,
                        help='Set web server listening port', default=5000)
    parser.add_argument('-L', '--locale',
                        help='Locale for Pokemon names (default: {},\
                        check {} for more)'.
                        format(config['LOCALE'], config['LOCALES_DIR']), default='en')
    parser.add_argument('-c', '--china',
                        help='Coordinates transformer for China',
                        action='store_true')
    parser.add_argument('-m', '--mock', type=str,
                        help='Mock mode - point to a fpgo endpoint instead of using the real PogoApi, ec: http://127.0.0.1:9090',
                        default='')
    parser.add_argument('-ns', '--no-server',
                        help='No-Server Mode. Starts the searcher but not the Webserver.',
                        action='store_true', default=False)
    parser.add_argument('-os', '--only-server',
                        help='Server-Only Mode. Starts only the Webserver without the searcher.',
                        action='store_true', default=True)
    parser.add_argument('-nsc', '--no-search-control',
                        help='Disables search control',
                        action='store_false', dest='search_control', default=True)
    parser.add_argument('-fl', '--fixed-location',
                        help='Hides the search bar for use in shared maps.',
                        action='store_true', default=False)
    parser.add_argument('-k', '--gmaps-key',
                        help='Google Maps Javascript API Key',
                        required=True)
    parser.add_argument('--spawnpoints-only', help='Only scan locations with spawnpoints in them.',
                        action='store_true', default=False)
    parser.add_argument('-C', '--cors', help='Enable CORS on web server',
                        action='store_true', default=False)
    parser.add_argument('-D', '--db', help='Database filename',
                        default='pogom.db')
    parser.add_argument('-cd', '--clear-db',
                        help='Deletes the existing database before starting the Webserver.',
                        action='store_true', default=False)
    parser.add_argument('-np', '--no-pokemon',
                        help='Disables Pokemon from the map (including parsing them into local db)',
                        action='store_true', default=False)
    parser.add_argument('-ng', '--no-gyms',
                        help='Disables Gyms from the map (including parsing them into local db)',
                        action='store_true', default=False)
    parser.add_argument('-nk', '--no-pokestops',
                        help='Disables PokeStops from the map (including parsing them into local db)',
                        action='store_true', default=False)
    parser.add_argument('-ss', '--spawnpoint-scanning',
                        help='Use spawnpoint scanning (instead of hex grid)', nargs='?', const='nofile', default=False)
    parser.add_argument('--dump-spawnpoints', help='dump the spawnpoints from the db to json (only for use with -ss)',
                        action='store_true', default=False)
    parser.add_argument('-pd', '--purge-data',
                        help='Clear pokemon from database this many hours after they disappear \
                        (0 to disable)', type=int, default=0)
    parser.add_argument('-px', '--proxy', help='Proxy url (e.g. socks5://127.0.0.1:9050)')
    parser.add_argument('--db-type', help='Type of database to be used (default: sqlite)',
                        default='sqlite')
    parser.add_argument('--db-name', help='Name of the database to be used')
    parser.add_argument('--db-user', help='Username for the database')
    parser.add_argument('--db-pass', help='Password for the database')
    parser.add_argument('--db-host', help='IP or hostname for the database')
    parser.add_argument('--db-port', help='Port for the database', type=int, default=3306)
    parser.add_argument('--db-max_connections', help='Max connections (per thread) for the database',
                        type=int, default=100)
    parser.add_argument('--db-threads', help='Number of db threads; increase if the db queue falls behind',
                        type=int, default=1)
    parser.add_argument('-wh', '--webhook', help='Define URL(s) to POST webhook information to',
                        nargs='*', default=False, dest='webhooks')
    parser.add_argument('-gi', '--gym-info', help='Get all details about gyms (causes an additional API hit for every gym)',
                        action='store_true', default=True)
    parser.add_argument('--webhook-updates-only', help='Only send updates (pokémon & lured pokéstops)',
                        action='store_true', default=False)
    parser.add_argument('--wh-threads', help='Number of webhook threads; increase if the webhook queue falls behind',
                        type=int, default=1)
    parser.add_argument('--ssl-certificate', help='Path to SSL certificate file')
    parser.add_argument('--ssl-privatekey', help='Path to SSL private key file')
    parser.add_argument('-ps', '--print-status', action='store_true',
                        help='Show a status screen instead of log messages. Can switch between status and logs by pressing enter.', default=False)
    parser.add_argument('-el', '--encrypt-lib', help='Path to encrypt lib to be used instead of the shipped ones')
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument('-v', '--verbose', help='Show debug messages from PomemonGo-Map and pgoapi. Optionally specify file to log to.', nargs='?', const='nofile', default=False, metavar='filename.log')
    verbosity.add_argument('-vv', '--very-verbose', help='Like verbose, but show debug messages from all modules as well.  Optionally specify file to log to.', nargs='?', const='nofile', default=False, metavar='filename.log')
    verbosity.add_argument('-d', '--debug', help='Depreciated, use -v or -vv instead.', action='store_true')
    parser.set_defaults(DEBUG=False)

    args = parser.parse_args()

    if args.only_server:
        if args.location is None:
            parser.print_usage()
            print(sys.argv[0] + ": error: arguments -l/--location is required")
            sys.exit(1)
    else:
        errors = []

        num_auths = 1
        num_usernames = 0
        num_passwords = 0

        if (args.username is None):
            errors.append('Missing `username` either as -u/--username or in config')
        else:
            num_usernames = len(args.username)

        if (args.location is None):
            errors.append('Missing `location` either as -l/--location or in config')

        if (args.password is None):
            errors.append('Missing `password` either as -p/--password or in config')
        else:
            num_passwords = len(args.password)

        if (args.step_limit is None):
            errors.append('Missing `step_limit` either as -st/--step-limit or in config')

        if args.auth_service is None:
            args.auth_service = ['ptc']
        else:
            num_auths = len(args.auth_service)

        if num_usernames > 1:
            if num_passwords > 1 and num_usernames != num_passwords:
                errors.append('The number of provided passwords ({}) must match the username count ({})'.format(num_passwords, num_usernames))
            if num_auths > 1 and num_usernames != num_auths:
                errors.append('The number of provided auth ({}) must match the username count ({})'.format(num_auths, num_usernames))

        if len(errors) > 0:
            parser.print_usage()
            print(sys.argv[0] + ": errors: \n - " + "\n - ".join(errors))
            sys.exit(1)

        # Fill the pass/auth if set to a single value
        if num_passwords == 1:
            args.password = [args.password[0]] * num_usernames
        if num_auths == 1:
            args.auth_service = [args.auth_service[0]] * num_usernames

        # Make our accounts list
        args.accounts = []

        # Make the accounts list
        for i, username in enumerate(args.username):
            args.accounts.append({'username': username, 'password': args.password[i], 'auth_service': args.auth_service[i]})

    return args


def insert_mock_data(position):
    num_pokemon = 6
    num_pokestop = 6
    num_gym = 6

    log.info('Creating fake: %d pokemon, %d pokestops, %d gyms',
             num_pokemon, num_pokestop, num_gym)

    from .models import Pokemon, Pokestop, Gym
    from .search import generate_location_steps

    latitude, longitude = float(position[0]), float(position[1])

    locations = [l for l in generate_location_steps((latitude, longitude), num_pokemon, 0.07)]
    disappear_time = datetime.now() + timedelta(hours=1)

    detect_time = datetime.now()

    for i in range(1, num_pokemon):
        Pokemon.create(encounter_id=uuid.uuid4(),
                       spawnpoint_id='sp{}'.format(i),
                       pokemon_id=(i + 1) % 150,
                       latitude=locations[i][0],
                       longitude=locations[i][1],
                       disappear_time=disappear_time,
                       detect_time=detect_time)

    for i in range(1, num_pokestop):
        Pokestop.create(pokestop_id=uuid.uuid4(),
                        enabled=True,
                        latitude=locations[i + num_pokemon][0],
                        longitude=locations[i + num_pokemon][1],
                        last_modified=datetime.now(),
                        # Every other pokestop be lured
                        lure_expiration=disappear_time if (i % 2 == 0) else None,
                        )

    for i in range(1, num_gym):
        Gym.create(gym_id=uuid.uuid4(),
                   team_id=i % 3,
                   guard_pokemon_id=(i + 1) % 150,
                   latitude=locations[i + num_pokemon + num_pokestop][0],
                   longitude=locations[i + num_pokemon + num_pokestop][1],
                   last_modified=datetime.now(),
                   enabled=True,
                   gym_points=1000
                   )


def now():
    # The fact that you need this helper...
    return int(time.time())


def i8ln(word):
    if config['LOCALE'] == "en":
        return word
    if not hasattr(i8ln, 'dictionary'):
        file_path = os.path.join(
            config['ROOT_PATH'],
            config['LOCALES_DIR'],
            '{}.min.json'.format(config['LOCALE']))
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                i8ln.dictionary = json.loads(f.read())
        else:
            log.warning('Skipping translations - Unable to find locale file: %s', file_path)
            return word
    if word in i8ln.dictionary:
        return i8ln.dictionary[word]
    else:
        log.debug('Unable to find translation for "%s" in locale %s!', word, config['LOCALE'])
        return word


def get_pokemon_data(pokemon_id):
    if not hasattr(get_pokemon_data, 'pokemon'):
        file_path = os.path.join(
            config['ROOT_PATH'],
            config['DATA_DIR'],
            'pokemon.min.json')

        with open(file_path, 'r') as f:
            get_pokemon_data.pokemon = json.loads(f.read())
    return get_pokemon_data.pokemon[str(pokemon_id)]


def get_pokemon_name(pokemon_id):
    return i8ln(get_pokemon_data(pokemon_id)['name'])


def get_pokemon_rarity(pokemon_id):
    return i8ln(get_pokemon_data(pokemon_id)['rarity'])


def get_pokemon_types(pokemon_id):
    pokemon_types = get_pokemon_data(pokemon_id)['types']
    return map(lambda x: {"type": i8ln(x['type']), "color": x['color']}, pokemon_types)


def get_encryption_lib_path(args):
    if args.encrypt_lib is not None:
        lib_path = args.encrypt_lib

        if not os.path.isfile(lib_path):
            err = "Could not find manually specified encryption library {}".format(lib_path)
            log.error(err)
            raise Exception(err)
    else:
        # win32 doesn't mean necessarily 32 bits
        if sys.platform == "win32" or sys.platform == "cygwin":
            if platform.architecture()[0] == '64bit':
                lib_name = "encrypt64bit.dll"
            else:
                lib_name = "encrypt32bit.dll"

        elif sys.platform == "darwin":
            lib_name = "libencrypt-osx-64.so"

        elif os.uname()[4].startswith("arm") and platform.architecture()[0] == '32bit':
            lib_name = "libencrypt-linux-arm-32.so"

        elif os.uname()[4].startswith("aarch64") and platform.architecture()[0] == '64bit':
            lib_name = "libencrypt-linux-arm-64.so"

        elif sys.platform.startswith('linux'):
            if "centos" in platform.platform():
                if platform.architecture()[0] == '64bit':
                    lib_name = "libencrypt-centos-x86-64.so"
                else:
                    lib_name = "libencrypt-linux-x86-32.so"
            else:
                if platform.architecture()[0] == '64bit':
                    lib_name = "libencrypt-linux-x86-64.so"
                else:
                    lib_name = "libencrypt-linux-x86-32.so"

        elif sys.platform.startswith('freebsd'):
            lib_name = "libencrypt-freebsd-64.so"

        else:
            err = "Unexpected/unsupported platform '{}'. If you have encrypt lib compiled for your platform, specify its location with '--encrypt-lib' parameter".format(sys.platform)
            log.error(err)
            raise Exception(err)

        lib_path = os.path.join(os.path.dirname(__file__), "libencrypt", lib_name)

        if not os.path.isfile(lib_path):
            err = "Could not find {} encryption library {}".format(sys.platform, lib_path)
            log.error(err)
            raise Exception(err)

    return lib_path


class Timer():

    def __init__(self, name):
        self.times = [(name, time.time(), 0)]

    def add(self, step):
        t = time.time()
        self.times.append((step, t, round((t - self.times[-1][1]) * 1000)))

    def checkpoint(self, step):
        t = time.time()
        self.times.append(('total @ ' + step, t, t - self.times[0][1]))

    def output(self):
        self.checkpoint('end')
        pprint.pprint(self.times)