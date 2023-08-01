import json

import boto3
from boto3.dynamodb.conditions import Attr, Key

dynamodb_resource = boto3.resource("dynamodb")
file_table_resource = dynamodb_resource.Table("file_table")


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


inputs = {
    "filetype": ".mp3",
    "redacted": False,
}
get_items_from_table_filetype_redacted(inputs)
