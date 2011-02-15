import os
from setuptools import setup, find_packages
version = '0.1.0'
README = os.path.join(os.path.dirname(__file__), 'README.md')
long_description = open(README).read()
setup(name='django-apiserver',
      version=version,
      description=("An API generation framework for Django."),
      long_description=long_description,
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Web Environment',
                   'Framework :: Django',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'Topic :: Utilities'],
      keywords='api REST',
      author='Stijn Debrouwere, Daniel Lindsley',
      author_email='stijn@stdout.be',
      url='http://camayak.github.com/django-apiserver/',
      download_url='http://www.github.com/camayak/django-apiserver/tarball/master',
      license='BSD',
      packages=find_packages(),
      install_requires=['simplejson'],
      )
