import os
from setuptools import setup

__version__ = '0.3.0'


with open(os.path.join(os.path.dirname(__file__), 'CHANGES.rst')) as fp:
  LONG_DESCRIPTION = fp.read()


setup(
  name='compactor',
  version=__version__,
  description='Pure python implementation of libprocess actors',
  long_description=LONG_DESCRIPTION,
  url='http://github.com/wickman/compactor',
  author='Brian Wickman',
  author_email='wickman@gmail.com',
  license='Apache License 2.0',
  packages=['compactor'],
  install_requires=[
    'trollius',
    'tornado==4.1',
    'twitter.common.lang',
  ],
  extras_require={
    'pb': ['protobuf>=2.6.1,<2.7'],
  },
  zip_safe=True,
)
