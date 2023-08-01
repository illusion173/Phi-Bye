import os
from datetime import date

import boto3

# This constant ensures anything that will be censored has .8 confidence
CONFIDENCE = 0.8

s3_client = boto3.client("s3")


def get_transcript(source_bucket, source_key):
    transcript = ""

    response = s3_client.get_object(Bucket=source_bucket, Key=source_key)
    transcript = response.get("Body").read().decode()
    return transcript


def get_entity_map(response):
    print(response)
    entities = response["Entities"]
    entity_map = {}

    for entity in entities:
        entity_map[entity["Text"]] = entity["Type"]

    return entity_map


def remove_phi_from_transcript(entity_map, transcript):
    redacted_transcript = transcript
    for k, v in entity_map.items():
        redacted_transcript = redacted_transcript.replace(k, v)
    return redacted_transcript


def start_comprehend_medical_job(source_bucket, source_key):
    transcript = get_transcript(source_bucket, source_key)
    comprehend_medical_client = boto3.client("comprehendmedical")

    response = comprehend_medical_client.detect_phi(Text=transcript)
    entity_map = get_entity_map(response)

    redacted_transcript = remove_phi_from_transcript(entity_map, transcript)
    return redacted_transcript


def start_comprehend_job(transcript):
    comprehend_client = boto3.client("comprehend")

    response = comprehend_client.detect_entities(Text=transcript, LanguageCode="en")
    entity_map = get_entity_map(response)
    full_redacted = remove_phi_from_transcript(entity_map, transcript)

    return full_redacted


def upload_to_s3(destination_folder, destination_key, transcript):
    result_bucket_name = os.environ["RESULT_BUCKET_NAME"]
    response = s3_client.put_object(
        Body=transcript,
        Bucket=result_bucket_name,
        Key=destination_folder + "/redacted-" + destination_key,
    )
    upload_time = str(date.today().isoformat())
    return upload_time


def delete_from_bucket(Bucket_name, key_to_delete):
    response = s3_client.delete_object(Bucket=Bucket_name, Key=key_to_delete)


def lambda_handler(event, context):
    source_key = event["StatePayload"]["plain_text_key"]
    folder_UUID = event["Folder_UUID"]["UUID"]
    original_filename = event["Original_Filename"]["original_filename"]

    # So we have partially redacted
    in_text_bucket_name = os.environ["IN_TEXT_PHI_BUCKET_NAME"]
    redacted_medical_transcript = start_comprehend_medical_job(
        in_text_bucket_name, source_key
    )
    # Now for full redacted
    redacted_full_transcript = start_comprehend_job(redacted_medical_transcript)
    upload_time = upload_to_s3(folder_UUID, source_key, redacted_full_transcript)
    s3_key, file_extension = os.path.splitext(source_key)
    delete_from_bucket(in_text_bucket_name, source_key)

    return {
        "plain_text_key": s3_key,
        "final_result_folder": folder_UUID,
        "original_filename": original_filename,
        "time_uploaded": upload_time,
    }
