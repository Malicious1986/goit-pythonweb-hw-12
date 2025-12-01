# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import sys
import os

sys.path.append(os.path.abspath(".."))

project = "Rest API"
copyright = "2025, Yurii Osadchyi"
author = "Yurii Osadchyi"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "nature"
html_static_path = ["_static"]


def skip_member(app, what, name, obj, skip, options):
    """Skip documenting certain members that cause noisy warnings.

    We skip attributes named ``metadata`` (SQLAlchemy MetaData) because the
    upstream SQLAlchemy docstring contains Sphinx labels that are undefined in
    this project's docs and generate warnings.
    """
    if name == "metadata":
        return True
    return None


def setup(app):
    app.connect("autodoc-skip-member", skip_member)
