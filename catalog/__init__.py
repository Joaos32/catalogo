from fastapi import APIRouter

# create a router that will be mounted under `/catalog` by the main app
catalog_router = APIRouter()

# import routes after defining the router so they can register themselves
from . import routes
