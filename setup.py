from distutils.core import setup


setup(
    name='bob',
    version='0.0.1',
    description='A Docker Compose building tool',
    author='Greg Chalmers',
    author_email='ops@metocean.co.nz',

    packages=['bob'],

    package_data={'bob':
                  ['static/css/*.css',
                   'static/fonts/*.*',
                   'static/images/*.*',
                   'static/js/*.*',
                   'templates/*.*']},
)
