from dapr.actor.runtime.runtime import ActorRuntime
from dapr.actor.runtime.config import (
    ActorRuntimeConfig,
    ActorTypeConfig,
    ActorReentrancyConfig,
)
from fastapi import FastAPI
import uvicorn
from dapr.ext.fastapi import DaprActor
from py_a2a_dapr.actor.hello_world import HelloWorldActor

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("WE ARE HERE")
    dapr_actor = DaprActor(app)
    await ActorRuntime.register_actor(HelloWorldActor)
    await dapr_actor.register_actor(HelloWorldActor)
    yield


app = FastAPI(
    title=f"{HelloWorldActor.__name__} Service",
    # We should be using lifespan instead of on_event
    # lifespan=lifespan
)

config = ActorRuntimeConfig()
config.update_actor_type_configs(
    [
        ActorTypeConfig(
            actor_type=HelloWorldActor.__name__,
            reentrancy=ActorReentrancyConfig(enabled=True),
        )
    ]
)
ActorRuntime.set_actor_config(config)

dapr_actor = DaprActor(app)


@app.on_event("startup")
async def startup_event():
    await ActorRuntime.register_actor(HelloWorldActor)
    await dapr_actor.register_actor(HelloWorldActor)


def main():
    uvicorn.run(app, host="127.0.0.1", port=16799)


if __name__ == "__main__":
    main()
