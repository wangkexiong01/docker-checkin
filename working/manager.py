# -*- coding:utf-8 -*-
import importlib
import logging.config
import os
import string
import sys
from random import choice
from string import Template

import yaml
from flask.ext.script import Manager, Server, Shell, prompt_bool

logger = logging.getLogger('root')

app4name = None
running_app = None


def make_app(app_name):
    try:
        global app4name
        global running_app

        app4name = app_name
        running_app = importlib.import_module(app_name)
        return running_app.create_app()
    except (ImportError, AttributeError):
        print('%s is not proper programming here.....' % app4name)
        exit(-1)


manager = Manager(make_app)
manager.add_option('-n', '--name', dest="app_name", required=True)


def _make_context():
    if hasattr(running_app, 'db'):
        return dict(app=manager.app, db=running_app.db)
    else:
        return dict(app=manager.app)


manager.add_command("shell", Shell(make_context=_make_context))
manager.add_command('runserver', Server('0.0.0.0', port=5000))


@manager.command
def createall():
    """Creates database tables"""
    if hasattr(running_app, 'db') and hasattr(running_app.db, 'create_all'):
        before_create = set(running_app.db.engine.table_names())
        running_app.db.create_all()

        if hasattr(running_app, 'import_data'):
            running_app.import_data()

        after_create = set(running_app.db.engine.table_names())
        for table in (after_create - before_create):
            print 'Created table: {}'.format(table)
        print


@manager.command
def dropall():
    """Drops all database tables"""
    if hasattr(running_app, 'db') and hasattr(running_app.db, 'drop_all'):
        if prompt_bool("Are you sure ? You will lose all your data !"):
            running_app.db.drop_all()


@manager.command
def compile_babel():
    """compile messages.po file for i18n"""

    from colorama import init, Fore
    init(autoreset=True)

    cmd = 'pybabel compile -d %s/translations' % app4name
    print(Fore.RED + 'Running: %s' % cmd)
    os.system(cmd)


@manager.option('-h', '--host', dest='host', default='0.0.0.0')
@manager.option('-p', '--port', dest='port', type=int, default=5000)
@manager.option('-w', '--workers', dest='workers', type=int, default=3)
@manager.option('-t', '--timeout', dest='timeout', type=int, default=90)
def run_gunicorn(host, port, workers, timeout):
    """Start the Server with Gunicorn"""
    from gunicorn.app.base import Application

    class FlaskApplication(Application):
        def init(self, parser, opts, args):
            return {
                'bind': '{0}:{1}'.format(host, port),
                'workers': workers, 'timeout': timeout
            }

        def load(self):
            return manager.app

    application = FlaskApplication()
    return application.run()


@manager.option("-f", "--force", dest="force",
                help="force overwrite of existing secret_keys file", action="store_true")
@manager.option("-r", "--randomness", dest="randomness",
                help="length (randomness) of generated key; default = 24", default=24)
def gen_csrfkey(force, randomness):
    """Generate random keys for CSRF and session key"""

    def gen_randomkey(length):
        """Generate random key, given a number of characters"""
        chars = string.letters + string.digits + string.punctuation
        return ''.join([choice(chars) for _ in xrange(int(str(length)))])

    csrf_key = gen_randomkey(randomness)
    session_key = gen_randomkey(randomness)

    file_name = '%s/secret_keys.py' % app4name
    file_template = Template('''# CSRF and Session keys

CSRF_SECRET_KEY = '$csrf_key'
SESSION_KEY = '$session_key'
''')

    output = file_template.safe_substitute(dict(
        csrf_key=csrf_key, session_key=session_key
    ))

    if (os.path.exists(file_name)) and (force is False):
        print "Warning: secret_keys.py file exists.  Use '-f' flag to force overwrite."
    else:
        f = open(file_name, 'wb')
        f.write(output)
        f.close()


@manager.option("-k", "--keywords", dest="keywords", default='',
                help='keywords to look for in addition to the defaults.\
                      Use "," to separate multiple inputs on the command line.')
@manager.option("-l", "--language", dest="language", required=True,
                help='generate messages.po for that locale')
def init_babel(keywords, language):
    """Generate messages.po file for i18n"""

    para = ''
    for keyword in keywords.split(','):
        if keyword.strip() != '':
            para += '-k %s ' % keyword

    from colorama import init, Fore
    init(autoreset=True)

    cmd = 'pybabel extract -F babel.cfg %s -o %s/translations/messages.pot %s' % \
          (para, app4name, app4name)
    print(Fore.RED + 'Running: %s' % cmd)
    os.system(cmd)

    cmd = 'pybabel init -i %s/translations/messages.pot -d %s/translations -l %s' % \
          (app4name, app4name, language)
    print(Fore.RED + 'Running: %s' % cmd)
    os.system(cmd)


@manager.option("-k", "--keywords", dest="keywords", default='',
                help='keywords to look for in addition to the defaults.\
                      Use "," to separate multiple inputs on the command line.')
def update_babel(keywords):
    """Update already generated messages.po file for i18n"""

    para = ''
    for keyword in keywords.split(','):
        if keyword.strip() != '':
            para += '-k %s ' % keyword

    from colorama import init, Fore
    init(autoreset=True)

    cmd = 'pybabel extract -F babel.cfg %s -o %s/translations/messages.pot %s' % \
          (para, app4name, app4name)
    print(Fore.RED + 'Running: %s' % cmd)
    os.system(cmd)

    cmd = 'pybabel update -i %s/translations/messages.pot -d %s/translations' % \
          (app4name, app4name)
    print(Fore.RED + 'Running: %s' % cmd)
    os.system(cmd)


if __name__ == "__main__":
    log_config = 'instance/logging.yaml'
    logging.config.dictConfig(yaml.load(open(log_config, 'r')))

    app_namespace, _ = manager.create_parser(sys.argv[0]).parse_known_args(sys.argv[1:])
    kwargs = app_namespace.__dict__
    if 'app_name' in kwargs:
        try:
            running_jobs = importlib.import_module(kwargs['app_name'] + '.jobs')
            running_jobs.configure_jobs()
        except (ImportError, AttributeError):
            pass

    manager.run()
