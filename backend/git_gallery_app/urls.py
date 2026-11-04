# Add API routes here. They are served under /api/.

from django.urls import path
from .views import (
    hello_world,
    get_repository,
    project_gallery,
    project_detail,
    project_analyses,
    check_repository_compatibility,
)

urlpatterns = [
    path("hello/", hello_world, name="hello-world"),
    path("repo/info/", get_repository, name="get-repository-info"),
    path("projects/", project_gallery, name="project-gallery"),
    path("projects/<str:project_id>/", project_detail, name="project-detail"),
    path(
        "projects/<str:project_id>/analyses/",
        project_analyses,
        name="project-analyses",
    ),
    path(
        "repo/compatibility/",
        check_repository_compatibility,
        name="check-repository-compatibility",
    ),
]
