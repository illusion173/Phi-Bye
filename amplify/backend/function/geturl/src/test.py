import json
import logging

import boto3
import botocore
from boto3.dynamodb.conditions import Attr, Key
from botocore import client
from botocore.exceptions import ClientError

dynamodb_resource = boto3.resource("dynamodb")

file_table_resource = dynamodb_resource.Table("file_table")


def gets3iteminfo(inputs):
    info = {}

    response = file_table_resource.query(
        IndexName="original_filename-index",
        # Select="S",
        # ProjectionExpression="UUID, s3_key, filetype",
        KeyConditionExpression=Key("original_filename").eq(inputs["original_filename"]),
        FilterExpression=Attr("redacted").eq(inputs["redacted"])
        & Attr("filetype").eq(inputs["filetype"]),
    )
    UUID = response["Items"][0]["UUID"]
    s3_key = response["Items"][0]["s3_key"]
    filetype = response["Items"][0]["filetype"]
    info["Key"] = UUID + "/" + s3_key + filetype
    info["Bucket"] = "result-bucket-illusjw"
    return info


def getpresignedurl(info):
    url = ""
    s3_client = boto3.client("s3", config=client.Config(signature_version="s3v4"))
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": info["Bucket"], "Key": info["Key"]},
            ExpiresIn=300,
        )
        print(response)
    except Exception as e:
        print(e)
        logging.error(e)
        return "Error"
    return url


def str2bool(v):
    return v.lower() in ("True", "true")


def handler(event, context):
    checkbool = str2bool(event["queryStringParameters"]["redacted"])
    inputs = {
        "original_filename": event["queryStringParameters"]["original_filename"],
        "redacted": checkbool,
        "filetype": event["queryStringParameters"]["filetype"],
    }
    info = gets3iteminfo(inputs)
    presignedurl = getpresignedurl(info)
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        },
        "body": json.dumps(presignedurl),
    }


inputs = {
    "queryStringParameters": {
        "original_filename": "original-audio",
        "redacted": "True",
        "filetype": ".txt",
    }
}
handler(inputs, {})
