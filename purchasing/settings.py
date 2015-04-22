# -*- coding: utf-8 -*-
import os

os_env = os.environ

class Config(object):
    SECRET_KEY = os_env.get('PITTSBURGH-PURCHASING-SUITE_SECRET', 'secret-key')  # TODO: Change me
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    ASSETS_DEBUG = False
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.

class ProdConfig(Config):
    """Production configuration."""
    ENV = 'prod'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os_env.get('DATABASE_URL', 'postgresql://localhost/purchasing')  # TODO: Change me
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar

class DevConfig(Config):
    """Development configuration."""
    ENV = 'dev'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os_env.get('DATABASE_URL', 'postgresql://localhost/purchasing') # TODO: Change me
    DEBUG_TB_ENABLED = True
    ASSETS_DEBUG = True  # Don't bundle/minify static assets

class TestConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os_env.get('DATABASE_URL', 'postgresql://localhost/purchasing_test')
    WTF_CSRF_ENABLED = False  # Allows form testing
