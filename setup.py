from distutils.core import setup


setup(
    name='bob_the_builder',
    version='0.0.1',
    description='A Docker Compose building tool',
    author='Greg Chalmers',
    author_email='ops@metocean.co.nz',

    packages=['bob_the_builder'],

    package_data={'bob_the_builder':
                  ['static/css/*.css',
                   'static/fonts/*.*',
                   'static/images/*.*',
                   'static/js/*.*',
                   'templates/*.*']},
)
