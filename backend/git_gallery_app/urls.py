# Add API routes here. They are served under /api/.

from django.urls import path
from .views import hello_world, get_repository, get_commits, create_analysis

urlpatterns = [
    path("hello/", hello_world, name="hello-world"),
    path("repo/info/", get_repository, name="get-repository-info"),
    path("repo/commits/", get_commits, name="get-repository-commits"),
    path("analyses/", create_analysis, name="create-analysis"),
]
