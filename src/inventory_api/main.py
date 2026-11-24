import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from inventory_api.database import get_session
from inventory_api.models import Item
from inventory_api.schemas import ItemInput, ItemOutput
from inventory_api.security import require_api_key_configuration, verify_api_key

SessionDependency = Annotated[Session, Depends(get_session)]
logger = logging.getLogger("inventory_api.requests")
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the inventory API.",
    ("method", "handler", "status"),
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "handler"),
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema changes are applied by the versioned migration step, not at API startup.
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Inventory Management API",
        version="1.0.0",
        description="A small inventory service with health and Prometheus metrics endpoints.",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        handler = getattr(route, "path", "/unmatched")
        duration = time.perf_counter() - started
        if handler != "/metrics":
            REQUEST_COUNT.labels(request.method, handler, str(response.status_code)).inc()
            REQUEST_DURATION.labels(request.method, handler).observe(duration)
        logger.info(
            json.dumps(
                {
                    "method": request.method,
                    "path": handler,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
                separators=(",", ":"),
            )
        )
        return response

    @application.get("/metrics", include_in_schema=False, tags=["health"])
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @application.get("/health/live", tags=["health"])
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", tags=["health"])
    def readiness(session: SessionDependency) -> dict[str, str]:
        require_api_key_configuration()
        session.execute(text("SELECT 1"))
        return {"status": "ready"}

    @application.get(
        "/items",
        response_model=list[ItemOutput],
        dependencies=[Depends(verify_api_key)],
        tags=["items"],
    )
    def list_items(
        session: SessionDependency,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[Item]:
        return list(session.scalars(select(Item).order_by(Item.id).offset(offset).limit(limit)))

    @application.post(
        "/items",
        response_model=ItemOutput,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(verify_api_key)],
        tags=["items"],
    )
    def create_item(item: ItemInput, session: SessionDependency) -> Item:
        record = Item(**item.model_dump())
        session.add(record)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An item with SKU '{item.sku}' already exists.",
            ) from error
        session.refresh(record)
        return record

    @application.get(
        "/items/{item_id}",
        response_model=ItemOutput,
        dependencies=[Depends(verify_api_key)],
        tags=["items"],
    )
    def get_item(item_id: int, session: SessionDependency) -> Item:
        item = session.get(Item, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
        return item

    @application.put(
        "/items/{item_id}",
        response_model=ItemOutput,
        dependencies=[Depends(verify_api_key)],
        tags=["items"],
    )
    def replace_item(item_id: int, item: ItemInput, session: SessionDependency) -> Item:
        record = session.get(Item, item_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
        for field, value in item.model_dump().items():
            setattr(record, field, value)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An item with SKU '{item.sku}' already exists.",
            ) from error
        session.refresh(record)
        return record

    @application.delete(
        "/items/{item_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        dependencies=[Depends(verify_api_key)],
        tags=["items"],
    )
    def delete_item(item_id: int, session: SessionDependency) -> Response:
        item = session.get(Item, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
        session.delete(item)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return application


app = create_app()
