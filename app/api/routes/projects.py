from fastapi import APIRouter, status

from app.api.deps import CurrentUser, ProjectServiceDep
from app.schemas.project import ProjectRead, ProjectWriteRequest

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(user: CurrentUser, service: ProjectServiceDep) -> list[ProjectRead]:
    return [ProjectRead.model_validate(p) for p in service.list_for_user(user)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectWriteRequest, user: CurrentUser, service: ProjectServiceDep
) -> ProjectRead:
    return ProjectRead.model_validate(service.create(user, payload))


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: str,
    payload: ProjectWriteRequest,
    user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectRead:
    return ProjectRead.model_validate(service.update(project_id, user, payload))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: CurrentUser, service: ProjectServiceDep) -> None:
    service.delete(project_id, user)
