"""
Quick fix to add an approximation (mtime) to date added before we tracked it.
"""

from skid import config
from skid.add import Document

from datetime import datetime

for f in config.CACHE.files():

    d = Document(f)
    mtime = str(datetime.fromtimestamp((f + '.d').mtime))

    # won't overwrite
    d.store('data/date-added', mtime, overwrite=False)
