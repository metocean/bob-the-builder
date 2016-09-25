from setuptools import setup

setup(
    name='bob',
    version='0.2.0',
    description='A Docker Compose building tool',
    author='Greg Chalmers',
    author_email='ops@metocean.co.nz',

    packages=['bob',
              'bob.common',
              'bob.cli',
              'bob.worker',
              'bob.webserver'],

    package_data={'bob':
                  ['webserver/static/css/*.css',
                   'webserver/static/fonts/*.*',
                   'webserver/static/images/*.*',
                   'webserver/static/js/*.*',
                   'webserver/templates/*.*']},

    entry_points={
        'console_scripts': ['bob=bob.cli.bob_cli:main'],
    }
)
