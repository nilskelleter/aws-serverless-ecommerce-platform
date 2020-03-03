"""
CreateOrderFunction
"""


import asyncio
import datetime
import json
import os
from typing import List, Tuple
import uuid
import boto3
import jsonschema
from aws_lambda_powertools.tracing import Tracer # pylint: disable=import-error
from aws_lambda_powertools.logging import logger_setup, logger_inject_lambda_context # pylint: disable=import-error


ENVIRONMENT = os.environ["ENVIRONMENT"]
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.json")
TABLE_NAME = os.environ["TABLE_NAME"]


dynamodb = boto3.resource("dynamodb") # pylint: disable=invalid-name
table = dynamodb.Table(TABLE_NAME) # pylint: disable=invalid-name,no-member
logger = logger_setup() # pylint: disable=invalid-name
tracer = Tracer() # pylint: disable=invalid-name


with open(SCHEMA_FILE) as fp:
    schema = json.load(fp) # pylint: disable=invalid-name


@tracer.capture_method
async def validate_delivery(order: dict) -> Tuple[bool, str]:
    """
    Validate the delivery price
    """

    # TODO
    return (True, "")


@tracer.capture_method
async def validate_payment(order: dict) -> Tuple[bool, str]:
    """
    Validate the payment token
    """

    # TODO
    return (True, "")


@tracer.capture_method
async def validate_products(order: dict) -> Tuple[bool, str]:
    """
    Validate the products in the order
    """

    # TODO
    return (True, "")


async def validate(order: dict) -> List[str]:
    """
    Returns a list of error messages
    """

    error_msgs = []
    for valid, error_msg in await asyncio.gather(
            validate_delivery(order),
            validate_payment(order),
            validate_products(order)):
        if not valid:
            error_msgs.append(error_msg)

    if error_msgs:
        logger.info({
            "message": "Validation errors for order",
            "order": order,
            "errors": error_msgs
        })

    return error_msgs


@tracer.capture_method
def inject_order_fields(order: dict) -> dict:
    """
    Inject fields into the order and return the order
    """

    now = datetime.datetime.now()

    order["orderId"] = str(uuid.uuid4())
    order["createdDate"] = now.isoformat()
    order["modifiedDate"] = now.isoformat()
    order["total"] = sum([p["price"]*p.get("quantity", 1) for p in order["products"]]) + order["deliveryPrice"]

    return order


@tracer.capture_method
def store_order(order: dict) -> None:
    """
    Store the order in DynamoDB
    """

    logger.debug({
        "message": "Store order",
        "order": order
    })

    table.put_item(Item=order)


@logger_inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda function handler
    """

    # Basic checks on the event
    assert "order" in event
    assert "userId" in event

    # Inject userId into the order
    order = event["order"]
    order["userId"] = event["userId"]

    # Validate the schema of the order
    try:
        jsonschema.validate(order, schema)
    except jsonschema.ValidationError as exc:
        return {
            "statusCode": 400,
            "message": "JSON Schema validation error",
            "errors": [str(exc)]
        }

    # Inject fields in the order
    order = inject_order_fields(order)

    # Validate the order against other services
    error_msgs = asyncio.run(validate(order))
    if len(error_msgs) > 0:
        return {
            "statusCode": 400,
            "message": "Validation errors",
            "errors": error_msgs
        }

    store_order(order)

    return {
        "statusCode": 200,
        "message": "Order created"
    }
