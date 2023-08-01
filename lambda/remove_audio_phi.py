import json
import os
import uuid
from datetime import date
from pathlib import Path

import boto3

s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")
dynamodb_resource = boto3.resource("dynamodb")
table = dynamodb_resource.Table("file_table")
dynamodb_client = boto3.client("dynamodb")
from boto3.dynamodb.conditions import Key

folder_input_uuid = ""
original_filename_global = ""
INAUDIOPHIBUCKET = "in-audio-phi"
new_transcript_uuid = ""


def load_transcript_json(transcript_item_list):
    # Get the json document
    transcript_file = ""
    bucket = transcript_item_list[0]
    key = transcript_item_list[1]
    try:
        transcript_file = (
            s3_resource.Object(bucket, key).get()["Body"].read().decode("utf-8")
        )
    except Exception as e:
        print(e)

    # Delete transcript file (cleanup of cache)
    try:
        delete_from_bucket(bucket, key)
    except Exception as e:
        print(e)

    return json.loads(transcript_file)


def delete_from_bucket(Bucket_name, key_to_delete):
    response = s3_client.delete_object(Bucket=Bucket_name, Key=key_to_delete)


def upload_plaintext_transcript(transcript_string):
    global new_transcript_uuid
    new_transcript_uuid = str(uuid.uuid4())
    # Put into worker bucket
    response = s3_client.put_object(
        Body=transcript_string, Bucket="in-text-phi", Key=new_transcript_uuid + ".txt"
    )
    # Put into result bucket
    response = s3_client.put_object(
        Body=transcript_string,
        Bucket="result-bucket-illusjw",
        Key=folder_input_uuid + "/" + new_transcript_uuid + ".txt",
    )
    update_dynamodb(
        folder_input_uuid,
        original_filename_global,
        new_transcript_uuid,
        3,
        "",
        False,
        ".txt",
    )


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


def get_uuid(filename):
    uuid = ""
    response = table.query(
        IndexName="s3_key-index", KeyConditionExpression=Key("s3_key").eq(filename)
    )
    uuid = response["Items"][0]["UUID"]
    original_filename = response["Items"][0]["original_filename"]
    return uuid, original_filename


def remove_audio_phi(entity_time_stamps, file):
    command_str_p1 = "/opt/bin/ffmpeg -i "
    redact_times = ""
    for time_stamps in entity_time_stamps:
        s = (
            "volume=enable='between(t,"
            + str(time_stamps[0])
            + ","
            + str(time_stamps[1])
            + ")':volume=0"
            + ", "
        )
        redact_times += s

    redact_times = '"' + redact_times[:-2] + '"'
    try:
        os.system(
            command_str_p1
            + "/tmp/"
            + file
            + " -af "
            + redact_times
            + " /tmp/redacted-"
            + file
        )

    except Exception as e:
        print(e)
    filename, file_extension = os.path.splitext(file)
    try:
        # Find appropriate folder
        uuid, original_filename = get_uuid(filename)
        global folder_input_uuid, original_filename_global
        folder_input_uuid = uuid
        original_filename_global = original_filename

        # move to appropriate result bucket & Folder
        response = s3_client.upload_file(
            "/tmp/redacted-" + file,
            "result-bucket-illusjw",
            uuid + "/" + "redacted-" + file,
        )
        # update dynamoodb
        update_dynamodb(
            uuid, original_filename, filename, 2, "redacted-", True, file_extension
        )

    except Exception as e:
        print(e)


def parse_url(url: str):
    scheme_end = url.find("://")
    netloc_start = scheme_end + 3
    netloc_end = url.find("/", netloc_start)
    path_start = netloc_end
    path_end = url.rfind("/") + 1
    path = url[path_start:path_end]
    path = path[1:]
    filename = url[path_end:]

    return path, filename


def lambda_handler(event, context):
    # First get bucket / key of mp3
    mediaurl = event["Media"]["MediaFileUri"]
    path, file = parse_url(mediaurl)

    # Second get bucket / key of transcript
    transcripturl = event["Transcript"]["TranscriptFileUri"]
    path, filename = parse_url(transcripturl)
    split_items = path.split("/")
    transcript_url_data = [
        split_items[0],
        split_items[1] + "/" + filename,
    ]

    try:
        s3_resource.Bucket(INAUDIOPHIBUCKET).download_file(file, "/tmp/" + file)

    except Exception as e:
        print(e)

    transcript_json = load_transcript_json(transcript_url_data)
    transcript_results = transcript_json["results"]
    transcript_string = transcript_results["transcripts"][0]["transcript"]
    transcript_entities = transcript_results["entities"]

    entity_time_stamps = []

    for entity in transcript_entities:
        entity_time_stamps.append([entity["start_time"], entity["end_time"]])

    remove_audio_phi(entity_time_stamps, file)

    # Delete from worker bucket?
    try:
        delete_from_bucket(INAUDIOPHIBUCKET, file)
    except Exception as e:
        print(e)
        return {"StatusCode": 500}

    # Put plain_text_transcript in s3 bucket
    upload_plaintext_transcript(transcript_string)
    # need to send transcript data here in return result
    return {
        "Transcript": {"plain_text_key": new_transcript_uuid + ".txt"},
        "Folder_UUID": {"UUID": folder_input_uuid},
        "Original_Filename": {"original_filename": original_filename_global},
    }
