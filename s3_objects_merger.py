import boto3

from botocore.exceptions import ClientError
from io import BytesIO

BODY = 'Body'
CONTENTS = 'Contents'
DOT = '.'
KEY = 'Key'
LINE_BREAK = '\n'

SUCCESS_NO_EXTENSION = '_SUCCESS'
SUCCESS_WITH_CRC_EXTENSION = f'.{SUCCESS_NO_EXTENSION}.crc'


class S3ObjectsMerger:

    def merge(self,
              bucket_name: str,
              new_object_key: str,
              objects_to_merge_initial_name: str,
              objects_to_merge_prefix='',
              is_success_files_deletion_enabled=True):

        self.__check_if_bucket_exists(bucket_name)

        client = boto3.client('s3')
        objects = client.list_objects_v2(Bucket=bucket_name, Prefix=objects_to_merge_prefix)

        if CONTENTS in objects:
            new_object = ''
            new_object_extension = new_object_key.split(DOT)[-1]

            for object_content in objects[CONTENTS]:
                object_name = object_content[KEY].split('/')[-1]
                object_to_merge_key = f'{objects_to_merge_prefix}{object_name}'

                if object_name.startswith(objects_to_merge_initial_name):
                    if object_name.endswith(new_object_extension):
                        object_to_merge = client.get_object(Bucket=bucket_name, Key=object_to_merge_key)
                        new_object = self.__merge_objects_line_by_line(object_to_merge, new_object)
                    client.delete_object(Bucket=bucket_name, Key=object_to_merge_key)

            with BytesIO(new_object[:-1].encode()) as file_obj:
                client.upload_fileobj(Bucket=bucket_name, Key=f'{new_object_key}', Fileobj=file_obj)

            if is_success_files_deletion_enabled:
                self.__delete_success_objects(client, bucket_name, objects_to_merge_prefix)

            client.close()

    @staticmethod
    def __check_if_bucket_exists(bucket_name):
        try:
            boto3.resource('s3').meta.client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise BucketNotFoundException('Bucket not found!')

    @staticmethod
    def __merge_objects_line_by_line(object_to_merge, new_object):
        for object_line_to_merge in object_to_merge[BODY].iter_lines():
            line_to_merge = object_line_to_merge.decode()
            new_object += f'{line_to_merge}{LINE_BREAK}'

        return new_object

    @staticmethod
    def __delete_success_objects(client, bucket_name, objects_to_merge_prefix):
        success_objects = [SUCCESS_NO_EXTENSION, SUCCESS_WITH_CRC_EXTENSION]
        for obj in success_objects:
            client.delete_object(Bucket=bucket_name, Key=f'{objects_to_merge_prefix}{obj}')


class BucketNotFoundException(Exception):
    pass
