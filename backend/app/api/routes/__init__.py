# API routes package.
#
# main.py imports `products` and `sales` as modules and includes them directly:
#     from app.api.routes import products
#     app.include_router(products)
#
# For that to work, `products` and `sales` must be the ROUTER OBJECTS, not the
# modules. The two lines below alias the routers so main.py's imports resolve
# correctly.

from app.api.routes.products import router as products  # noqa: F401
from app.api.routes.sales import router as sales  # noqa: F401