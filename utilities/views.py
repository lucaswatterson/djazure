from django.views.generic import TemplateView


class DemoView(TemplateView):
    template_name = "pages/demo.html"
