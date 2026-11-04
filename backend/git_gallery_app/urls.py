# Add API routes here. They are served under /api/.

from django.urls import path
from .views import hello_world, get_repository, check_repository_compatibility

urlpatterns = [
    path("hello/", hello_world, name="hello-world"),
    path("repo/info/", get_repository, name="get-repository-info"),
    path(
        "repo/compatibility/",
        check_repository_compatibility,
        name="check-repository-compatibility",
    ),
]
