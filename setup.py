from setuptools import setup, find_packages

setup(
    name='bob',
    version='0.2.1',
    description='A Docker Compose building tool',
    author='Greg Chalmers',
    author_email='ops@metocean.co.nz',

    packages=find_packages(),

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
