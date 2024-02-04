"""Using AI vision to extract damaged parts in a hypothetical
insurance claim using Marvin and Prefect interactive workflows.

authored by: @kevingrismore and @zzstoatzz
"""
from enum import Enum
from typing import TypeVar

import marvin
from prefect import flow, pause_flow_run, task
from prefect.artifacts import create_markdown_artifact
from prefect.input import RunInput
from prefect.settings import PREFECT_UI_URL
from prefect.tasks import task_input_hash
from pydantic import BaseModel, Field, create_model

M = TypeVar("M", bound=RunInput)


class Severity(str, Enum):
    minor = "minor"
    moderate = "moderate"
    severe = "severe"


class DamagedPart(BaseModel):
    part: str = Field(
        description="short unique name for a damaged part",
        example="front_left_bumper",
    )
    severity: Severity = Field(description="objective severity of part damage")
    description: str = Field(description="specific high level summary in 1 sentence")


class Car(BaseModel):
    id: str
    image_url: str


def build_damage_report_model(damages: list[DamagedPart]) -> M:
    """TODO we should be able to have a static `DamageReportInput` model with
    a `list[DamagedPart]` field but it won't be rendered nice yet.
    """
    return create_model(
        "DamageReportInput",
        **{f"{damage.part}": (DamagedPart, ...) for damage in damages},
        __base__=RunInput,
    )


@task(cache_key_fn=task_input_hash)
def marvin_evaluate_damage(image_url: str) -> list[DamagedPart]:
    return marvin.beta.extract(
        data=marvin.beta.Image(image_url),
        target=DamagedPart,
        instructions=(
            "Give extremely brief, high-level descriptions of the damage."
            " Only include the 2 most significant damages, which may also be minor and/or moderate."
            # only want 2 damages for purposes of this example
        ),
    )


@task
async def submit_damage_report(report: M, car: Car):
    """submit the damage report to a system of record"""
    uuid = await create_markdown_artifact(
        key=f"latest-damage-report-car-{car.id}",
        markdown=(
            f"## **Damage Report for Car {car.id}**\n"
            f"![image]({car.image_url})\n**Data:**\n"
            f"```json\n{report.model_dump_json(indent=2)}\n```"
        ),
        description=f"## Latest damage report for car {car.id}",
    )
    print(
        f"See your artifact in the UI: {PREFECT_UI_URL.value()}/artifacts/artifact/{uuid}"
    )


@flow(log_prints=True)
async def process_damage_report(car: Car):
    damaged_parts = sorted(marvin_evaluate_damage(car.image_url), key=lambda x: x.part)

    DamageReportInput: type[M] = build_damage_report_model(damaged_parts)

    damage_report = await pause_flow_run(
        wait_for_input=DamageReportInput.with_initial_data(
            description=(
                "🔍 audit the damage report drafted from submitted image:"
                f"\n![image]({car.image_url})"
            ),
            **dict(zip(DamageReportInput.model_fields.keys(), damaged_parts)),
        )
    )
    print(f"Resumed flow run with damage report: {damage_report!r}")

    await submit_damage_report(damage_report, car)


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        process_damage_report(
            {
                "id": "1",  # or wherever you'd get your car data from
                "image_url": "https://cs.copart.com/v1/AUTH_svc.pdoc00001/lpp/0923/e367ca327c564c9ba8368359f456664f_ful.jpg",  # noqa E501
            }
        )
    )
