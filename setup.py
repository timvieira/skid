from setuptools import setup, find_packages

# TODO: should check for other dependencies such as pdftotex

# TODO: some stuff in sandbox uses scikits-learn

setup(name='skid',
      version='1.0',
      description='Skid: bookmarks, simply kept in directories',
      url='https://github.com/timvieira/skid/',
      packages= find_packages(),
      scripts=['bin/skid',
               'bin/pdf-hammer.py',
               'bin/ocr-pdf-searchable',
               'bin/ocr-pdf-extract-text',
               'skid/utils/gscholar.py'],
      install_requires=['whoosh', 'pdfminer', 'pandas', 'arsenal'])
