# Add API routes here. They are served under /api/.

from django.urls import path
from .views import hello_world

urlpatterns = [
    path("hello/", hello_world, name="hello-world"),
]
