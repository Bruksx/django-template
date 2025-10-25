from django.template import Template


class CustomHTMLTemplate(Template):

    def _render(self, context):
        text = super()._render(context)
        return "<br>".join(text.splitlines())