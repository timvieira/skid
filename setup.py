from setuptools import setup, find_packages

setup(name='skid',
      version='1.0',
      description='Skid: bookmarks, simply kept in directories',
      url='https://github.com/timvieira/skid/',
      packages= find_packages(),
      scripts=['bin/skid'],
      install_requires=['whoosh', 'pdfminer', 'pandas', 'arsenal'])
