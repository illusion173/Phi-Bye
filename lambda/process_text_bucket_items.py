import json
import os
import uuid
from datetime import date

import boto3
from boto3.dynamodb.conditions import Attr, Key

dynamodb_resource = boto3.resource("dynamodb")
dynamodb_client = boto3.client("dynamodb")
table = dynamodb_resource.Table("file_table")
TABLENAME = "file_Table"


# Update DynamoDb for new item
def update_dynamodb(
    uuid, original_filename, filename, file_num, prefix, redacted, file_type
):
    try:
        response = dynamodb_client.put_item(
            TableName="file_table",
            Item={
                "UUID": {"S": uuid},
                "file_num": {"N": str(file_num)},
                "original_filename": {"S": original_filename},
                "filetype": {"S": file_type},
                "redacted": {"BOOL": redacted},
                "s3_key": {"S": prefix + filename},
                "upload_date": {"S": str(date.today().isoformat())},
            },
        )
    except Exception as e:
        print(e)
        return {"statusCode": 500}


def create_folder_rename_file(original_filename):
    s3_client = boto3.client("s3")
    # We need to create a new s3 folder in result
    new_folder_UUID = str(uuid.uuid4())
    new_file_name_UUID = str(uuid.uuid4())

    # Create a folder for file
    print("Creating Folder")
    response = s3_client.put_object(
        Bucket="result-bucket-illusjw", Key=new_folder_UUID + "/"
    )
    # Copy object to result folder
    print("Copy to Result")
    response_copy_result = s3_client.copy_object(
        Bucket="result-bucket-illusjw",
        CopySource={"Bucket": "in-text-phi", "Key": original_filename + ".txt"},
        Key=new_folder_UUID + "/" + new_file_name_UUID + ".txt",
    )
    # copy object and put the new name on it
    print("Copying to in-text-phi, new name")
    response_copy_in_text = s3_client.copy_object(
        Bucket="in-text-phi",
        CopySource={"Bucket": "in-text-phi", "Key": original_filename + ".txt"},
        Key=new_file_name_UUID + ".txt",
    )

    # Then delete original

    print("Deleting original")
    response_delete_original = s3_client.delete_object(
        Bucket="in-text-phi", Key=original_filename + ".txt"
    )
    # We need to create a dynmodb entry for this item
    print("Update Dynamodb")
    update_dynamodb(
        new_folder_UUID, original_filename, new_file_name_UUID, "3", "", False, ".txt"
    )


def begin_step_function(folder_uuid, plain_text_key, original_filename):
    step_function_client = boto3.client("stepfunctions")
    input_dict = {
        "Original_Filename": {"original_filename": original_filename},
        "StatePayload": {"plain_text_key": plain_text_key},
        "Folder_UUID": {"UUID": folder_uuid},
    }
    response = step_function_client.start_execution(
        stateMachineArn="arn:aws:states:us-west-2:042288440768:stateMachine:text-stepfunc",
        input=json.dumps(input_dict),
    )

    return None


def check_if_folder_exists(s3_key):
    response = table.query(
        IndexName="s3_key-index", KeyConditionExpression=Key("s3_key").eq(s3_key)
    )
    folder_UUID = ""
    if response["Items"]:
        print(response)
        print("Has parent folder")
        folder_UUID = response["Items"][0]["UUID"]
        original_filename = response["Items"][0]["original_filename"]
        plain_text_key = response["Items"][0]["s3_key"] + ".txt"
        # from here we start the step function!
        begin_step_function(folder_UUID, plain_text_key, original_filename)

    else:
        print("Has no parent folder, creating now!")
        create_folder_rename_file(s3_key)


def lambda_handler(event, context):
    s3_full_key = event["detail"]["object"]["key"]
    s3_key, file_extension = os.path.splitext(s3_full_key)
    check_if_folder_exists(s3_key)
    return {"statusCode": 200, "body": json.dumps("Hello from Lambda!")}
