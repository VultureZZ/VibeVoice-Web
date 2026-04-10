"""
Runtime settings endpoints.
"""

from fastapi import APIRouter, HTTPException, status

from ..models.schemas import (
    AceStepModelCatalogResponse,
    AceStepRuntimeSettingsResponse,
    AceStepRuntimeSettingsUpdateRequest,
    ErrorResponse,
)
from ..services.acestep_settings import acestep_settings_service
from ..services.music_process import music_process_manager

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _compute_source() -> str:
    return "settings_file" if acestep_settings_service.storage_file.exists() else "env_defaults"


@router.get(
    "/acestep",
    response_model=AceStepRuntimeSettingsResponse,
    responses={500: {"model": ErrorResponse}},
)
async def get_acestep_runtime_settings() -> AceStepRuntimeSettingsResponse:
    values = acestep_settings_service.get_current()
    return AceStepRuntimeSettingsResponse(
        acestep_config_path=values["acestep_config_path"],
        acestep_lm_model_path=values["acestep_lm_model_path"],
        source=_compute_source(),
        restart_required=music_process_manager.is_running(),
        settings_file=str(acestep_settings_service.storage_file),
    )


@router.put(
    "/acestep",
    response_model=AceStepRuntimeSettingsResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def update_acestep_runtime_settings(
    request: AceStepRuntimeSettingsUpdateRequest,
) -> AceStepRuntimeSettingsResponse:
    previous = acestep_settings_service.get_current()
    try:
        updated = acestep_settings_service.update(
            acestep_config_path=request.acestep_config_path,
            acestep_lm_model_path=request.acestep_lm_model_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    changed = updated != previous
    was_running = music_process_manager.is_running()
    if changed and was_running:
        music_process_manager.stop()

    return AceStepRuntimeSettingsResponse(
        acestep_config_path=updated["acestep_config_path"],
        acestep_lm_model_path=updated["acestep_lm_model_path"],
        source=_compute_source(),
        restart_required=changed and was_running,
        settings_file=str(acestep_settings_service.storage_file),
    )


@router.get(
    "/acestep/models",
    response_model=AceStepModelCatalogResponse,
    responses={500: {"model": ErrorResponse}},
)
async def get_acestep_model_catalog() -> AceStepModelCatalogResponse:
    catalog = acestep_settings_service.get_catalog()
    return AceStepModelCatalogResponse(**catalog)
