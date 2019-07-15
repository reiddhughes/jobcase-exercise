import pytest

import boto3
import create_instance
import moto


@pytest.fixture
def mock_client():
    with moto.mock_ec2():
        client = boto3.client('ec2', region_name='us-east-1')
        response = client.run_instances(ImageId='', MinCount=1, MaxCount=1)
        instance_id = response['Instances'][0]['InstanceId']
        client.create_image(InstanceId=instance_id, Name='jobcase-test-app')
        client.terminate_instances(InstanceIds=[instance_id])

        yield client


def test_add_image_id_to_specification(mock_client):
    ami = create_instance.AmazonMachineImage(
        client=mock_client,
        name='jobcase-test-app',
        is_public=False
    )

    specification = {}
    ami.add_image_id_to_specification(specification=specification)

    assert specification['ImageId']


def test_cannot_find_public_image(mock_client):
    ami = create_instance.AmazonMachineImage(
        client=mock_client,
        name='jobcase-test-app',
        is_public=True
    )

    specification = {}

    with pytest.raises(create_instance.ImageMissingError):
        ami.add_image_id_to_specification(specification=specification)


def test_cannot_find_missing_image(mock_client):
    ami = create_instance.AmazonMachineImage(
        client=mock_client,
        name='missing-image-name',
        is_public=False
    )

    specification = {}

    with pytest.raises(create_instance.ImageMissingError):
        ami.add_image_id_to_specification(specification=specification)


def test_cannot_find_missing_public_image(mock_client):
    ami = create_instance.AmazonMachineImage(
        client=mock_client,
        name='missing-image-name',
        is_public=True
    )

    specification = {}

    with pytest.raises(create_instance.ImageMissingError):
        ami.add_image_id_to_specification(specification=specification)


def test_to_string_private(mock_client):
    ami = create_instance.AmazonMachineImage(
        client=mock_client,
        name='jobcase-test-app',
        is_public=False
    )

    assert str(ami) == "Image with name: jobcase-test-app and is-public: False"


def test_to_string_public(mock_client):
    ami = create_instance.AmazonMachineImage(
        client=mock_client,
        name='jobcase-test-app',
        is_public=True
    )

    assert str(ami) == "Image with name: jobcase-test-app and is-public: True"
