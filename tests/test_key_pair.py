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


def test_add_key_pair_to_specification(
        mock_client,
        mock_operating_system,
        mock_open_strategy
):

    key_pair = create_instance.KeyPair(
        key_name='aws-key',
        client=mock_client,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy
    )

    specification = {}
    key_pair.add_key_name_to_specification(specification=specification)

    assert specification['KeyName']


def test_create_in_all_client(
        mock_client,
        mock_operating_system,
        mock_open_strategy
):

    key_pair = create_instance.KeyPair(
        key_name='aws-key',
        client=mock_client,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy
    )

    key_pair.create_in_all_locations()
    key_description = mock_client.describe_key_pairs(KeyNames=['aws-key'])

    assert len(key_description['KeyPairs']) == 1


def test_create_in_all_file(
        mock_client,
        mock_operating_system,
        mock_open_strategy
):

    key_pair = create_instance.KeyPair(
        key_name='aws-key',
        client=mock_client,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy
    )

    key_pair.create_in_all_locations()
    local_key_path = '/Users/tester/.ssh/aws-key.pem'

    mock_open_strategy.assert_called_once_with(local_key_path, mode='w')


def test_create_in_all_file_chmod(
        mock_client,
        mock_operating_system,
        mock_open_strategy
):

    key_pair = create_instance.KeyPair(
        key_name='aws-key',
        client=mock_client,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy
    )

    key_pair.create_in_all_locations()
    local_key_path = '/Users/tester/.ssh/aws-key.pem'

    mock_operating_system.chmod.assert_called_once_with(local_key_path, 0o600)
