"""Finished analyses, kept in memory: they cost money and time, so identical requests are served from here.

The cache is empty again after every restart.
"""

analysis_cache: dict = {}
