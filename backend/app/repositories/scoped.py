"""Consultas de domínio sempre recebem tenant e escopo de permissão."""

from sqlalchemy import func, select

from app.api.dependencies import fail


def scoped(model, principal, permission, unit_column=None):
    query = select(model).where(model.organization_id == principal.user.organization_id)
    if principal.scopes[permission] is not None:
        units = principal.scopes[permission]
        if unit_column is not None:
            query = query.where(unit_column.in_(units))
    return query


def get_scoped(session, model, entity_id, principal, permission, unit_column=None):
    entity = session.scalar(scoped(model, principal, permission, unit_column).where(model.id == entity_id))
    if entity is None:
        fail(404, "NOT_FOUND", "Registro não encontrado.")
    return entity


def page(session, query, page_number, size, serialize):
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = session.scalars(query.offset((page_number - 1) * size).limit(size)).all()
    return {"items": [serialize(item) for item in items], "total": total, "page": page_number, "page_size": size}
