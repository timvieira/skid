from distutils.core import setup
import skid

setup(name='skid',
      version='1.0',
      description='Skid: bookmarks, simply kept in directories',
      #long_description=open('README.org').read(),
      author='Tim Vieira',
      url='https://github.com/timvieira/skid/',
      packages=['skid'],
      scripts=['bin/skid'],
      install_requires=['whoosh', 'pdfminer', 'numpy', 'pandas', 'ipython'],
     )
