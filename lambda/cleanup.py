import boto3

s3_resource = boto3.resource("s3")
# Set buckets
in_audio_phi_bucket = s3_resource.Bucket("in-audio-phi")
in_text_phi_bucket = s3_resource.Bucket("in-text-phi")
result_bucket = s3_resource.Bucket("result-bucket-illusjw")
# Get all objects and delete
in_audio_phi_bucket.objects.all().delete()
in_text_phi_bucket.objects.all().delete()
result_bucket.objects.all().delete()
