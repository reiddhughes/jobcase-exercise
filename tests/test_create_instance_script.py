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
def mock_subnet_id(mock_client):
    vpc_response = mock_client.create_vpc(CidrBlock='10.1.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    subnet_response = mock_client.create_subnet(
        CidrBlock='10.1.0.0/18',
        VpcId=vpc_id
    )

    subnet_id = subnet_response['Subnet']['SubnetId']

    return subnet_id


@pytest.fixture
def mock_boto3_library(mock_client):
    return boto3


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


def test_missing_key_name(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    with pytest.raises(SystemExit):
        script = create_instance.CreateInstanceScript(
            args=[],
            exit_strategy=exit,
            operating_system=mock_operating_system,
            open_strategy=mock_open_strategy,
            aws_library=mock_boto3_library
        )

        script.run()


@pytest.fixture
def env_with_region():
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

    yield

    os.environ.pop('AWS_DEFAULT_REGION')


@pytest.mark.usefixtures(env_with_region.__name__)
def test_region_env(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key'],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    script.run()


def test_region_arg(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key', '--region-name', 'us-east-1'],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    script.run()


@pytest.mark.usefixtures(env_with_region.__name__)
def test_public_image_missing(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key', '--image-is-public'],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    with pytest.raises(SystemExit):
        script.run()


@pytest.mark.usefixtures(env_with_region.__name__)
def test_bad_image_name_missing(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key', '--image-name', 'another-name'],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    with pytest.raises(SystemExit):
        script.run()


@pytest.mark.usefixtures(env_with_region.__name__)
def test_new_packages(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key', '--packages', 'ansible', 'postgres', 'nginx'],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    script.run()


@pytest.mark.usefixtures(env_with_region.__name__)
def test_new_instance_type(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key', '--instance-type', 't2.large'],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    script.run()


@pytest.mark.usefixtures(env_with_region.__name__)
def test_subnet_id(
        mock_operating_system,
        mock_open_strategy,
        mock_boto3_library,
        mock_subnet_id
):

    script = create_instance.CreateInstanceScript(
        args=['aws-key', '--subnet-id', mock_subnet_id],
        exit_strategy=exit,
        operating_system=mock_operating_system,
        open_strategy=mock_open_strategy,
        aws_library=mock_boto3_library
    )

    script.run()
