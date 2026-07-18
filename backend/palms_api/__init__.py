"""Pyramid application factory for the Palms API."""

from __future__ import annotations

import logging as stdlib_logging
from typing import Any, Mapping

from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPException
from pyramid.renderers import JSON
from pyramid.router import Router
from pyramid.tweens import EXCVIEW

from palms_api.config import Settings
from palms_api.database import Database
from palms_api.errors import (
    APIError,
    api_error_view,
    forbidden_view,
    http_exception_view,
    not_found_view,
    unexpected_error_view,
)
from palms_api.logging import configure_structured_logging
from palms_api.responses import json_dumps
from palms_api.auth_views import (
    change_password_view,
    forgot_password_view,
    login_view,
    logout_view,
    me_view,
    profile_change_email_view,
    profile_change_password_view,
    profile_get_view,
    profile_patch_view,
    reset_password_view,
    two_factor_disable_view,
    two_factor_enable_view,
    user_audit_logs_view,
    user_disable_view,
    user_enable_view,
    user_get_view,
    user_patch_view,
    user_reset_password_view,
    users_invite_view,
    users_list_view,
)
from palms_api.advanced_views import (
    dashboard_activity_view,
    dashboard_overview_view,
    palm_image_create_view,
    palm_image_delete_view,
    profile_avatar_create_view,
    public_donor_suggestions_view,
    public_palm_profile_view,
    public_search_view,
    report_generate_view,
    report_preview_view,
    report_run_download_view,
    report_schedule_create_view,
    report_schedule_delete_view,
    report_schedule_get_view,
    report_schedule_patch_view,
    report_schedule_pause_view,
    report_schedule_resume_view,
    report_schedule_runs_view,
    report_schedules_list_view,
    report_template_create_view,
    report_templates_list_view,
    report_types_view,
    section_image_create_view,
)
from palms_api.domain_views import (
    disease_create_view,
    disease_delete_view,
    disease_patch_view,
    donor_create_view,
    donor_delete_view,
    donor_get_view,
    donor_palms_view,
    donor_patch_view,
    donors_list_view,
    harvest_create_view,
    harvest_delete_view,
    harvest_patch_view,
    note_create_view,
    note_delete_view,
    palm_bulk_delete_view,
    palm_bulk_update_section_view,
    palm_create_view,
    palm_delete_view,
    palm_get_view,
    palm_patch_view,
    palms_list_view,
    relationship_create_view,
    relationship_delete_view,
    section_create_view,
    section_delete_view,
    section_get_view,
    section_patch_view,
    sections_list_view,
    treatment_create_view,
    treatment_delete_view,
    treatment_patch_view,
)
from palms_api.views import health_view, meta_view
from palms_api.email_service import EmailService
from palms_api.scheduler import report_executor
from palms_api.storage import build_storage_client

LOGGER = stdlib_logging.getLogger("palms_api")


def main(
    global_config: Mapping[str, Any] | None = None,
    **pyramid_settings: Any,
) -> Router:
    """Build the WSGI application with explicit runtime dependencies."""
    del global_config
    settings = Settings(**pyramid_settings)
    configure_structured_logging(settings.log_level)
    database = Database(settings)

    config = Configurator(settings=settings.pyramid_settings())
    config.registry.palms_settings = settings
    config.registry.palms_database = database
    storage = build_storage_client(settings)
    if settings.storage_provider == "s3" and settings.s3_create_bucket:
        storage.ensure_bucket()
    config.registry.palms_storage = storage
    config.registry.palms_email_service = EmailService(settings)
    config.registry.palms_report_executor = report_executor(
        settings, storage, config.registry.palms_email_service
    )
    config.add_request_method(database.session_for_request, "dbsession", reify=True)
    config.add_renderer("json", JSON(serializer=json_dumps))
    config.add_tween(
        "palms_api.logging.request_logging_tween_factory",
        over=EXCVIEW,
    )

    config.add_route("health", "/health")
    config.add_view(health_view, route_name="health", request_method="GET")
    config.add_route("api_meta", "/api/v1/meta")
    config.add_view(meta_view, route_name="api_meta", request_method="GET")

    _configure_auth_routes(config)
    _configure_admin_routes(config)
    _configure_public_routes(config)

    config.add_notfound_view(not_found_view)
    config.add_forbidden_view(forbidden_view)
    config.add_exception_view(api_error_view, context=APIError)
    config.add_exception_view(http_exception_view, context=HTTPException)
    config.add_exception_view(unexpected_error_view, context=Exception)

    LOGGER.info(
        "application_configured",
        extra={
            "event": "application_configured",
            "environment": settings.app_environment,
            "version": settings.app_version,
        },
    )
    return config.make_wsgi_app()


def _configure_auth_routes(config: Configurator) -> None:
    """Register versioned authentication endpoints."""
    routes = (
        ("auth_login", "/api/v1/auth/login", login_view, "POST"),
        ("auth_logout", "/api/v1/auth/logout", logout_view, "POST"),
        ("auth_me", "/api/v1/auth/me", me_view, "GET"),
        ("auth_forgot_password", "/api/v1/auth/forgot-password", forgot_password_view, "POST"),
        ("auth_reset_password", "/api/v1/auth/reset-password", reset_password_view, "POST"),
        ("auth_change_password", "/api/v1/auth/change-password", change_password_view, "POST"),
        ("auth_2fa_enable", "/api/v1/auth/2fa/enable", two_factor_enable_view, "POST"),
        ("auth_2fa_disable", "/api/v1/auth/2fa/disable", two_factor_disable_view, "POST"),
    )
    route_names: dict[str, str] = {}
    for name, pattern, view, method in routes:
        route_name = route_names.setdefault(pattern, name)
        if route_name == name:
            config.add_route(name, pattern)
        config.add_view(view, route_name=route_name, request_method=method)


def _configure_admin_routes(config: Configurator) -> None:
    """Register profile, user, and core administration resource routes."""
    routes = (
        ("admin_profile", "/api/v1/admin/profile", profile_get_view, "GET"),
        ("admin_profile_patch", "/api/v1/admin/profile", profile_patch_view, "PATCH"),
        (
            "admin_profile_change_password",
            "/api/v1/admin/profile/change-password",
            profile_change_password_view,
            "POST",
        ),
        (
            "admin_profile_change_email",
            "/api/v1/admin/profile/change-email",
            profile_change_email_view,
            "POST",
        ),
        ("admin_profile_avatar", "/api/v1/admin/profile/avatar", profile_avatar_create_view, "POST"),
        ("admin_dashboard_overview", "/api/v1/admin/dashboard/overview", dashboard_overview_view, "GET"),
        ("admin_dashboard_activity", "/api/v1/admin/dashboard/activity", dashboard_activity_view, "GET"),
        ("admin_users", "/api/v1/admin/users", users_list_view, "GET"),
        ("admin_users_invite", "/api/v1/admin/users/invite", users_invite_view, "POST"),
        ("admin_user_audit", "/api/v1/admin/users/{user_id}/audit-logs", user_audit_logs_view, "GET"),
        ("admin_user_disable", "/api/v1/admin/users/{user_id}/disable", user_disable_view, "POST"),
        ("admin_user_enable", "/api/v1/admin/users/{user_id}/enable", user_enable_view, "POST"),
        (
            "admin_user_reset_password",
            "/api/v1/admin/users/{user_id}/reset-password",
            user_reset_password_view,
            "POST",
        ),
        ("admin_user_get", "/api/v1/admin/users/{user_id}", user_get_view, "GET"),
        ("admin_user_patch", "/api/v1/admin/users/{user_id}", user_patch_view, "PATCH"),
        ("admin_donors", "/api/v1/admin/donors", donors_list_view, "GET"),
        ("admin_donor_create", "/api/v1/admin/donors", donor_create_view, "POST"),
        ("admin_donor_palms", "/api/v1/admin/donors/{donor_id}/palms", donor_palms_view, "GET"),
        ("admin_donor_get", "/api/v1/admin/donors/{donor_id}", donor_get_view, "GET"),
        ("admin_donor_patch", "/api/v1/admin/donors/{donor_id}", donor_patch_view, "PATCH"),
        ("admin_donor_delete", "/api/v1/admin/donors/{donor_id}", donor_delete_view, "DELETE"),
        ("admin_sections", "/api/v1/admin/sections", sections_list_view, "GET"),
        ("admin_section_create", "/api/v1/admin/sections", section_create_view, "POST"),
        ("admin_section_get", "/api/v1/admin/sections/{section_id}", section_get_view, "GET"),
        ("admin_section_patch", "/api/v1/admin/sections/{section_id}", section_patch_view, "PATCH"),
        ("admin_section_delete", "/api/v1/admin/sections/{section_id}", section_delete_view, "DELETE"),
        ("admin_section_image", "/api/v1/admin/sections/{section_id}/image", section_image_create_view, "POST"),
        ("admin_palms", "/api/v1/admin/palms", palms_list_view, "GET"),
        ("admin_palm_create", "/api/v1/admin/palms", palm_create_view, "POST"),
        ("admin_palm_bulk_delete", "/api/v1/admin/palms/bulk-delete", palm_bulk_delete_view, "POST"),
        (
            "admin_palm_bulk_update_section",
            "/api/v1/admin/palms/bulk-update-section",
            palm_bulk_update_section_view,
            "POST",
        ),
        ("admin_palm_image_create", "/api/v1/admin/palms/{palm_id}/images", palm_image_create_view, "POST"),
        ("admin_palm_image_delete", "/api/v1/admin/palms/{palm_id}/images/{image_id}", palm_image_delete_view, "DELETE"),
        (
            "admin_palm_harvest_create",
            "/api/v1/admin/palms/{palm_id}/harvests",
            harvest_create_view,
            "POST",
        ),
        (
            "admin_palm_harvest_patch",
            "/api/v1/admin/palms/{palm_id}/harvests/{harvest_id}",
            harvest_patch_view,
            "PATCH",
        ),
        (
            "admin_palm_harvest_delete",
            "/api/v1/admin/palms/{palm_id}/harvests/{harvest_id}",
            harvest_delete_view,
            "DELETE",
        ),
        (
            "admin_palm_disease_create",
            "/api/v1/admin/palms/{palm_id}/diseases",
            disease_create_view,
            "POST",
        ),
        (
            "admin_palm_disease_patch",
            "/api/v1/admin/palms/{palm_id}/diseases/{disease_id}",
            disease_patch_view,
            "PATCH",
        ),
        (
            "admin_palm_disease_delete",
            "/api/v1/admin/palms/{palm_id}/diseases/{disease_id}",
            disease_delete_view,
            "DELETE",
        ),
        (
            "admin_palm_treatment_create",
            "/api/v1/admin/palms/{palm_id}/diseases/{disease_id}/treatments",
            treatment_create_view,
            "POST",
        ),
        (
            "admin_palm_treatment_patch",
            "/api/v1/admin/palms/{palm_id}/diseases/{disease_id}/treatments/{treatment_id}",
            treatment_patch_view,
            "PATCH",
        ),
        (
            "admin_palm_treatment_delete",
            "/api/v1/admin/palms/{palm_id}/diseases/{disease_id}/treatments/{treatment_id}",
            treatment_delete_view,
            "DELETE",
        ),
        (
            "admin_palm_note_create",
            "/api/v1/admin/palms/{palm_id}/notes",
            note_create_view,
            "POST",
        ),
        (
            "admin_palm_note_delete",
            "/api/v1/admin/palms/{palm_id}/notes/{note_id}",
            note_delete_view,
            "DELETE",
        ),
        (
            "admin_palm_relationship_create",
            "/api/v1/admin/palms/{palm_id}/relationships",
            relationship_create_view,
            "POST",
        ),
        (
            "admin_palm_relationship_delete",
            "/api/v1/admin/palms/{palm_id}/relationships/{relationship_id}",
            relationship_delete_view,
            "DELETE",
        ),
        ("admin_palm_get", "/api/v1/admin/palms/{palm_id}", palm_get_view, "GET"),
        ("admin_palm_patch", "/api/v1/admin/palms/{palm_id}", palm_patch_view, "PATCH"),
        ("admin_palm_delete", "/api/v1/admin/palms/{palm_id}", palm_delete_view, "DELETE"),
        ("admin_report_types", "/api/v1/admin/reports/types", report_types_view, "GET"),
        ("admin_report_preview", "/api/v1/admin/reports/preview", report_preview_view, "POST"),
        ("admin_report_generate", "/api/v1/admin/reports/generate", report_generate_view, "POST"),
        ("admin_report_templates", "/api/v1/admin/reports/templates", report_templates_list_view, "GET"),
        ("admin_report_template_create", "/api/v1/admin/reports/templates", report_template_create_view, "POST"),
        ("admin_report_schedules", "/api/v1/admin/report-schedules", report_schedules_list_view, "GET"),
        ("admin_report_schedule_create", "/api/v1/admin/report-schedules", report_schedule_create_view, "POST"),
        ("admin_report_schedule_pause", "/api/v1/admin/report-schedules/{schedule_id}/pause", report_schedule_pause_view, "POST"),
        ("admin_report_schedule_resume", "/api/v1/admin/report-schedules/{schedule_id}/resume", report_schedule_resume_view, "POST"),
        ("admin_report_schedule_runs", "/api/v1/admin/report-schedules/{schedule_id}/runs", report_schedule_runs_view, "GET"),
        ("admin_report_schedule_get", "/api/v1/admin/report-schedules/{schedule_id}", report_schedule_get_view, "GET"),
        ("admin_report_schedule_patch", "/api/v1/admin/report-schedules/{schedule_id}", report_schedule_patch_view, "PATCH"),
        ("admin_report_schedule_delete", "/api/v1/admin/report-schedules/{schedule_id}", report_schedule_delete_view, "DELETE"),
        ("admin_report_run_download", "/api/v1/admin/report-runs/{run_id}/download", report_run_download_view, "GET"),
    )
    route_names: dict[str, str] = {}
    for name, pattern, view, method in routes:
        route_name = route_names.setdefault(pattern, name)
        if route_name == name:
            config.add_route(name, pattern)
        config.add_view(view, route_name=route_name, request_method=method)


def _configure_public_routes(config: Configurator) -> None:
    """Register intentionally unauthenticated, donor-safe public endpoints."""
    routes = (
        ("public_search", "/api/v1/public/search", public_search_view, "GET"),
        ("public_donor_suggestions", "/api/v1/public/donors/suggest", public_donor_suggestions_view, "GET"),
        ("public_palm_profile", "/api/v1/public/palms/{palm_code}", public_palm_profile_view, "GET"),
    )
    for name, pattern, view, method in routes:
        config.add_route(name, pattern)
        config.add_view(view, route_name=name, request_method=method)
