import json

import boto3
from boto3.dynamodb.conditions import Attr, Key

dynamodb_resource = boto3.resource("dynamodb")
file_table_resource = dynamodb_resource.Table("file_table")


# based on original filename and upload date
def get_items_from_table_filename_upload_date(inputs):
    response = file_table_resource.query(
        IndexName="original_filename-index",
        Select="SPECIFIC_ATTRIBUTES",
        ProjectionExpression="original_filename, redacted, upload_date, filetype",
        KeyConditionExpression=Key("original_filename").eq(
            inputs["original_filename_input"]
        ),
        FilterExpression=Attr("upload_date").eq(inputs["upload_date_input"]),
    )

    items = response["Items"]
    return items


# based only on upload_date
def get_items_from_table_upload_date(inputs):
    response = file_table_resource.query(
        IndexName="upload_date-index",
        Select="SPECIFIC_ATTRIBUTES",
        KeyConditionExpression=Key("upload_date").eq(inputs["upload_date_input"]),
        ProjectionExpression="original_filename, redacted, upload_date, filetype",
    )
    items = response["Items"]
    return items


# based on original_filename
def get_items_from_table_filename(inputs):
    response = file_table_resource.query(
        IndexName="original_filename-index",
        Select="SPECIFIC_ATTRIBUTES",
        KeyConditionExpression=Key("original_filename").eq(
            inputs["original_filename_input"]
        ),
        ProjectionExpression="original_filename, redacted, upload_date, filetype",
    )

    items = response["Items"]
    return items


def get_items_from_table_filetype_redacted(inputs):
    response = file_table_resource.query(
        IndexName="filetype-index",
        Select="SPECIFIC_ATTRIBUTES",
        KeyConditionExpression=Key("filetype").eq(inputs["filetype"]),
        FilterExpression=Attr("redacted").eq(inputs["redacted"]),
        ProjectionExpression="original_filename, redacted, upload_date, filetype",
    )
    items = response["Items"]
    return items


def str2bool(v):
    return v.lower() in ("True", "true")


def get_items(inputs):
    # Requires filetype & redacted status
    if inputs["filetype"] != "" and inputs["redacted"] is not None:
        print("filetype-redacted function")
        return get_items_from_table_filetype_redacted(inputs)
    # Requires only upload date
    if inputs["original_filename_input"] == "":
        return get_items_from_table_upload_date(inputs)
    # Requires only filename
    if inputs["upload_date_input"] == "":
        return get_items_from_table_filename(inputs)
    return get_items_from_table_filename_upload_date(inputs)


def handler(event, context):
    query_params = event["queryStringParameters"]

    inputs = {
        "original_filename_input": query_params["requested_filename"],
        "upload_date_input": query_params["upload_date"],
        "filetype": query_params["filetype"],
        "redacted": str2bool(query_params["redacted"]),
    }

    items = get_items(inputs)
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(items),
    }
