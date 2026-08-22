from parallax_api.main import create_app


def test_projects_router_is_registered_on_api_composition_root():
    app = create_app(create_schema=False)
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in app.routes}

    assert ("/v1/projects", ("POST",)) in routes
    assert ("/v1/projects", ("GET",)) in routes
    assert ("/v1/projects/{project_id}", ("GET",)) in routes
