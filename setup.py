from distutils.core import setup

setup(name='skid',
      version='1.0',
      description='Skid: bookmarks, simply kept in directories',
      author='Tim Vieira',
      url='https://github.com/timvieira/skid/',
      packages=['skid'],
      scripts=['bin/skid'],
      install_requires=['whoosh', 'pdfminer', 'pandas'])
