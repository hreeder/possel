#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import socket
import ssl

from OpenSSL import crypto
from pircel import model, tornado_adapter

from playhouse import db_url

import tornado.ioloop
import tornado.web
from tornado.web import url

from possel import auth, push, resources, web_client


def get_routes(interfaces):
    interface_routes = [url(r'/line', resources.LinesHandler),
                        url(r'/session', resources.SessionHandler, name='session'),
                        url(r'/buffer/([0-9]+|all)', resources.BufferGetHandler),
                        url(r'/buffer', resources.BufferPostHandler),
                        url(r'/server/([0-9]+|all)', resources.ServerGetHandler),
                        url(r'/server', resources.ServerPostHandler),
                        url(r'/user/([0-9]+|all)', resources.UserGetHandler),
                        url(r'/push', push.ResourcePusher, name='push'),
                        ]
    for route in interface_routes:
        route.kwargs.update(interfaces=interfaces)

    routes = [url(r'/', web_client.WebUIServer, name='index'),
              ] + interface_routes
    return routes


def generate_cert():
        # create a key pair
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().CN = socket.gethostname()
        cert.set_serial_number(1)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha1')

        cert_string = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        key_string = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        return cert_string, key_string


def get_ssl_context(args):
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(args.certificate, args.certificate.replace('crt', 'key'))
    return ssl_ctx


def get_relative_path(path):
    """ Gets the path of a file under the current directory """
    file_directory = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(file_directory, path)

settings = {'template_path': get_relative_path('data/templates'),
            'static_path': get_relative_path('data/static'),
            'cookie_secret': 'butts',
            'login_url': '/session',
            }


def get_etc_file(filename):
    return os.path.join('/etc/possel', filename)


def get_arg_parser():
    arg_parser = argparse.ArgumentParser(description='Possel Server')
    arg_parser.add_argument('-d', '--database', default='sqlite:///possel.db',
                            help='sqlalchemy-style database url string. See '
                            'http://peewee.readthedocs.org/en/latest/peewee/playhouse.html#db-url '
                            'for specification.')
    arg_parser.add_argument('-p', '--port', default=80,
                            help='Port possel server will listen on')
    arg_parser.add_argument('-b', '--bind-address', default='',
                            help='Address possel server will listen on (e.g. 0.0.0.0 for IPv4)')
    arg_parser.add_argument('-D', '--debug', action='store_true',
                            help='Turn on debug logging and show exceptions in the browser')
    arg_parser.add_argument('-c', '--certificate', default=get_etc_file('cert.pem'),
                            help='The X.509 certificate to present to clients')
    arg_parser.add_argument('-s', '--secure', action='store_true',
                            help='Enable SSL on the web server')
    arg_parser.add_argument('--log-irc', action='store_true',
                            help='Log lines from IRC verbatim in addition to any other logging')
    arg_parser.add_argument('--log-database', action='store_true',
                            help='Log all queries sent to the database.'
                            'Warning: *high* volume, requires --log-insecure')
    arg_parser.add_argument('--log-insecure', action='store_true',
                            help='Allow information in logs that attackers could use to compromise users. '
                            'WARNING: It\'s called "insecure" for a reason!')
    return arg_parser


def main():
    args = get_arg_parser().parse_args()

    # <setup logging>
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_date_format = "%Y-%m-%d %H:%M:%S"
    log_format = "%(asctime)s\t%(levelname)s\t%(module)s:%(funcName)s:%(lineno)d\t%(message)s"
    logging.basicConfig(level=log_level, format=log_format, datefmt=log_date_format)
    logging.captureWarnings(True)

    database_log_level = logging.DEBUG if args.log_database and args.log_insecure else logging.INFO
    logging.getLogger('peewee').setLevel(database_log_level)

    insecure_log_level = logging.DEBUG if args.log_insecure else logging.INFO
    logging.getLogger('insecure').setLevel(insecure_log_level)

    verbatim_log_level = logging.DEBUG if args.log_irc else logging.INFO
    logging.getLogger('pircel.protocol.verbatim').setLevel(verbatim_log_level)
    # </setup logging>

    settings['debug'] = args.debug

    db = db_url.connect(args.database)
    model.database.initialize(db)
    model.database.connect()
    model.initialize()
    auth.create_tables()

    interfaces = model.IRCServerInterface.get_all()
    clients = {interface_id: tornado_adapter.IRCClient.from_interface(interface)
               for interface_id, interface in interfaces.items()}
    for client in clients.values():
        client.connect()

    ssl_ctx = get_ssl_context(args) if args.secure else None

    application = tornado.web.Application(get_routes(interfaces), **settings)
    application.listen(args.port, args.bind_address, ssl_options=ssl_ctx)

    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
