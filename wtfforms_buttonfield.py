from markupsafe import Markup
from wtforms import Field


class ButtonField(Field):
    widget = None

    def __init__(self, label='', class_='btn', **kwargs):
        super(ButtonField, self).__init__(label, **kwargs)
        self.class_ = class_

    def _value(self):
        return self.data if self.data is not None else ''

    def process_formdata(self, valuelist):
        pass

    def __call__(self, **kwargs):
        button_html = '<button type="submit" class="{0}">{1}</button>'.format(self.class_, self.default)
        return Markup(button_html)
