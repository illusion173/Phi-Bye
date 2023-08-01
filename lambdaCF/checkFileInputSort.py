import os
import uuid
from datetime import date

import boto3

"""
RESULT_BUCKET_NAME: !Ref ResultPHIBucket
IN_TEXT_PHI_BUCKET_NAME: !Ref InTextPhiBucket
IN_AUDIO_PHI_BUCKET_NAME: !Ref InAudioPhiBucket
LANDING_IN_BUCKET_NAME: !Ref LandingInputPHIBucket
ERROR_BUCKET_NAME: !Ref ErrorPHIBucket
"""


s3_client = boto3.client("s3")
dynamodb_client = boto3.client("dynamodb")
FILE_TABLE_NAME = os.environ["FILE_TABLE_NAME"]


def update_dynamodb(
    uuid, original_filename, filename, file_num, prefix, redacted, file_type
):
    try:
        response = dynamodb_client.put_item(
            TableName=FILE_TABLE_NAME,
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


def move_file_to_error(source_bucket, source_key):
    print("ERROR! May be wrong file type")
    bucket_source_key = source_bucket + "/" + source_key
    new_fail_key = "wrongfiletype/" + source_key
    fail_bucket = os.environ["ERROR_BUCKET_NAME"]

    try:
        response_copy = s3_client.copy_object(
            Bucket=fail_bucket, CopySource=bucket_source_key, Key=new_fail_key
        )
    except Exception as e:
        print(e)
        return {"statusCode": 500}
    try:
        response_error = s3_client.delete_object(Bucket=source_bucket, Key=source_key)
    except Exception as e:
        print(e)
        return {"statusCode": 500}


def move_file(source_bucket, source_key, destination_bucket, file, file_extension):
    final_bucket = os.environ["RESULT_BUCKET_NAME"]

    key_input_folder = str(uuid.uuid4())
    new_file_name = str(uuid.uuid4())
    update_dynamodb(key_input_folder, file, new_file_name, "1", "", False, ".mp3")
    # move to final_result bucket
    new_key = key_input_folder + "/" + new_file_name + file_extension

    sourceOfFile = source_bucket + "/" + source_key

    # physical copy to bucket result bucket
    try:
        response_result = s3_client.copy_object(
            Bucket=final_bucket, CopySource=sourceOfFile, Key=new_key
        )
    except Exception as e:
        print(e)
        return e

    # physical copy to worker bucket
    try:
        response_worker = s3_client.copy_object(
            Bucket=destination_bucket,
            CopySource=sourceOfFile,
            Key=new_file_name + file_extension,
        )
    except Exception as e:
        print(e)
        return e

    # delete from landing bucket
    try:
        response_landing = s3_client.delete_object(Bucket=source_bucket, Key=source_key)
    except Exception as e:
        print(e)
        return e
    return 200


def move_to_worker_text(
    source_bucket, source_key, destination_bucket, file, file_extension
):
    # physical copy to worker bucket
    try:
        response_worker = s3_client.copy_object(
            Bucket=destination_bucket,
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Key=source_key,
        )
    except Exception as e:
        print(e)
        return e

    # delete from landing bucket
    LandingBucketName = os.environ["LANDING_IN_BUCKET_NAME"]

    try:
        response_landing = s3_client.delete_object(
            Bucket=LandingBucketName, Key=source_key
        )
    except Exception as e:
        print(e)
        return e
    return 200


def lambda_handler(event, context):
    source_key = event["Records"][0]["s3"]["object"]["key"]
    source_bucket = event["Records"][0]["s3"]["bucket"]["name"]

    text_input_bucket_name = os.environ["IN_TEXT_PHI_BUCKET_NAME"]
    audio_input_bucket_name = os.environ["IN_AUDIO_PHI_BUCKET_NAME"]
    file, file_extension = os.path.splitext(source_key)

    allowed_audio_extensions = [
        ".mp3",
        ".mp4",
        ".wav",
        ".flac",
        ".amr",
        ".ogg",
        ".webm",
        ".m4a",
    ]
    allowed_text_extensions = [".txt"]

    if file_extension in allowed_audio_extensions:
        move_file(
            source_bucket, source_key, audio_input_bucket_name, file, file_extension
        )
    elif file_extension in allowed_text_extensions:
        move_to_worker_text(
            source_bucket, source_key, text_input_bucket_name, file, file_extension
        )

    else:
        move_file_to_error(source_bucket, source_key)
        return {"statusCode": 422}
    return {"statusCode": 200}
