# Add API routes here. They are served under /api/.

from django.urls import path
from .views import hello_world, get_repository

urlpatterns = [
    path("hello/", hello_world, name="hello-world"),
    path("repo/info/", get_repository, name="get-repository-info"),
]
