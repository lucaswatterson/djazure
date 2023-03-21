from django.urls import path

from utilities.views import (
    DemoView,
)


app_name = "utilities"

urlpatterns = [
    path("", DemoView.as_view(), name="demo"),
]
