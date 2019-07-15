import os
from unittest import mock

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


@pytest.fixture
def mock_open_strategy():
    strategy = mock.mock_open()

    return strategy


@pytest.fixture
def mock_operating_system():
    operating_system = mock.Mock(spec_set=os)
    mock_path = mock.Mock(spec_set=os.path)
    operating_system.path = mock_path
    mock_path.sep = "/"
    mock_path.expanduser.side_effect = lambda x: x.replace(
        "~",
        '/Users/tester'
    )

    return operating_system


@pytest.fixture
def mock_image(mock_client):
    image = create_instance.AmazonMachineImage(
        client=mock_client,
        name='jobcase-test-app',
        is_public=False
    )

    return image


@pytest.fixture
def mock_key_pair(mock_client, mock_operating_system, mock_open_strategy):
    key_pair = create_instance.KeyPair(
        key_name='aws-key',
        client=mock_client,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy
    )

    return key_pair


def test_specify_key_pair_no_exception(mock_client, mock_image, mock_key_pair):
    builder = create_instance.InstanceBuilder(
        client=mock_client,
        machine_image=mock_image,
        instance_type='t2.micro'
    )

    builder.specify_key_pair(mock_key_pair)


def test_specify_subnet_id_no_exception(mock_client, mock_image):
    builder = create_instance.InstanceBuilder(
        client=mock_client,
        machine_image=mock_image,
        instance_type='t2.micro'
    )

    builder.specify_subnet_id(subnet_id='some-id')


def test_specify_create_instance(mock_client, mock_image, mock_key_pair):
    builder = create_instance.InstanceBuilder(
        client=mock_client,
        machine_image=mock_image,
        instance_type='t2.micro'
    )

    mock_key_pair.create_in_all_locations()
    builder.specify_key_pair(mock_key_pair)
    builder.specify_packages_to_install(["httpd",
                                         "mysql",
                                         "python",
                                         "logrotate",
                                         "aws-cli"])
    instance_id = builder.create_instance()
    response = mock_client.describe_instances(InstanceIds=[instance_id])

    assert len(response['Reservations'][0]['Instances']) == 1
