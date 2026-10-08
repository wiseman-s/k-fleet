import json
from fastapi.templating import Jinja2Templates

_templates = Jinja2Templates(directory="app/templates")

# Custom filters
_templates.env.filters["from_json"] = lambda s: json.loads(s) if s else {}


def get_templates() -> Jinja2Templates:
    return _templates