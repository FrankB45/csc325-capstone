# Add API routes here. They are served under /api/.

from django.urls import path
from .views import hello_world, get_repository, check_repository_compatibility, get_commits, create_analysis, get_project

urlpatterns = [
    path("hello/", hello_world, name="hello-world"),
    path("repo/info/", get_repository, name="get-repository-info"),
    path("repo/commits/", get_commits, name="get-repository-commits"),
    path("analyses/", create_analysis, name="create-analysis"),
    path("projects/<str:project_id>/", get_project, name="get-project"),
    path(
        "repo/compatibility/",
        check_repository_compatibility,
        name="check-repository-compatibility",
    ),
]
