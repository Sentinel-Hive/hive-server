import json
import shutil
import os

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'db_template.json')
DEFAULT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'db_template.json')


def load_db_template():
    """Load the current database template as a dict."""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_db_template(template_dict):
    """Save the given template dict to the template file."""
    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(template_dict, f, indent=2)


def edit_db_template(edit_func):
    """Edit the template using a provided function that takes and returns a dict."""
    template = load_db_template()
    new_template = edit_func(template)
    save_db_template(new_template)


def reset_db_template():
    """Reset the template to the default settings."""
    shutil.copyfile(DEFAULT_TEMPLATE_PATH, TEMPLATE_PATH)

import json
import shutil
import os

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'db_template.json')
DEFAULT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'db_template.json')


def load_db_template():
    """Load the current database template as a dict."""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_db_template(template_dict):
    """Save the given template dict to the template file."""
    with open(TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(template_dict, f, indent=2)


def edit_db_template(edit_func):
    """Edit the template using a provided function that takes and returns a dict."""
    template = load_db_template()
    new_template = edit_func(template)
    save_db_template(new_template)


def reset_db_template():
    """Reset the template to the default settings."""
    shutil.copyfile(DEFAULT_TEMPLATE_PATH, TEMPLATE_PATH)
