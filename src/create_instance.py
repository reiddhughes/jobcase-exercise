import argparse
import os
import sys

import boto3
from botocore import exceptions

"""
Module contains classes and __main__ method to support creating an instance in
AWS.  The module, when run, will parse arguments, create a key pair in the cloud
and locally, and finall create an instance.  The module is broken down into four
main classes: one to handle the Key Pair, one for the Image, one for the 
Instance creation, and one that handles the arguments and coordination.
"""


class KeyExistsError(Exception):
    """
    Raised when a Key Pair already exists on AWS.
    """

    pass


class ImageMissingError(Exception):
    """
    Raised when an AMI is not located on AWS according to the filters.
    """

    pass


class KeyPair(object):
    """
    Class that represents an AWS Key Pair.  Handles adding it to AWS and writing
    it locally.  Assumes that the Key Pair is not already present on AWS.
    """

    # noinspection PyUnresolvedReferences
    def __init__(
            self,
            key_name,
            client,
            operating_system,
            open_strategy
    ):
        """

        :param str key_name: Name of the key pair and the local key.  Local key
        is appended with ".pem".
        :param botocore_client.EC2 client: boto client connecting to EC2.
        :param os operating_system: Operating System object that has path and
        chown functions.
        :param open open_strategy: Callable used to open files for writing.
        """

        self._key_name = key_name
        self._client = client
        self._operating_system = operating_system
        self._open_strategy = open_strategy

    def add_key_name_to_specification(self, specification):
        """
        Add the key's name to the specification that is intended to be passed to
        AWS.

        :param dict specification: The specification mapping to be passed to
        AWS.
        :return None:
        """
        specification['KeyName'] = self._key_name

    def _assemble_local_path(self):
        ssh_directory_path = self._operating_system.path.expanduser('~/.ssh')
        key_file_name = "{key_name}.pem".format(key_name=self._key_name)
        local_path = self._operating_system.path.sep.join(
            [ssh_directory_path, key_file_name]
        )

        return local_path

    def _write_material_to_file(self, key_material):
        local_path = self._assemble_local_path()

        with self._open_strategy(local_path, mode='w') as key_file:
            key_file.write(key_material)

        self._operating_system.chmod(local_path, 0o600)

    def create_in_all_locations(self):
        """
        Creates the key pair in AWS and locally in the users .ssh folder.
        Appends ".pem" as the key extension.

        :return:
        """
        try:
            create_response = self._client.create_key_pair(
                KeyName=self._key_name,
            )

            key_material = create_response['KeyMaterial']
            self._write_material_to_file(key_material=key_material)

        except exceptions.ClientError as client_error:

            if 'InvalidKeyPair.Duplicate' in str(client_error):
                raise KeyExistsError(str(client_error))

            else:
                raise


class AmazonMachineImage(object):
    """
    Class that represents an Amazon Machine Image (AMI) on AWS.  Handles mapping
    image name to id and adding its id to a specification.  Assumes image is
    present on AWS.
    """

    # noinspection PyUnresolvedReferences
    def __init__(
            self,
            client,
            name,
            is_public
    ):
        """

        :param botocore_client.EC2 client:
        :param str name: Name of the AMI on AWS.  Looks up id with this.
        :param bool is_public: Flag that indicates whether or not the AMI is
        public on AWS.  Typically is not public.
        """

        self._client = client
        self._name = name
        self._is_public = is_public

    def _assemble_filters(self):
        name_filter = {"Name": "name", "Values": [self._name]}
        is_public_filter = {
            "Name": "is-public", "Values": [str(self._is_public).lower()]
        }

        filters = [name_filter, is_public_filter]

        return filters

    def _lookup_image_id(self):
        filters = self._assemble_filters()
        response = self._client.describe_images(Filters=filters)

        try:
            image_id = response['Images'][0]['ImageId']

            return image_id

        except IndexError:
            message = "{image} not found.".format(image=str(self))

            raise ImageMissingError(message)

    def add_image_id_to_specification(self, specification):
        """
        Adds the image id to the specification map intended to be passed to AWS
        when creating an instance.

        :param dict specification: The mapping that is intended to be passed to
        AWS.
        :return:
        """
        image_id = self._lookup_image_id()
        specification['ImageId'] = image_id

    def __str__(self):
        template = "Image with name: {name} and is-public: {is_public}"
        as_string = template.format(name=self._name, is_public=self._is_public)

        return as_string


class InstanceBuilder(object):
    """
    Class used to build AWS EC2 instance specifications and then create that
    instance.  Tags are hardcoded.  Supports installing packages with user data
    and cloud-init.  By default the key pair and subnet id are not specified.
    All required values are passed in through the constructor.  All optional
    values can be specified through their respective methods.
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, client, machine_image, instance_type):
        """

        :param botocore_client.EC2 client: boto client for AWS EC2.
        :param AmazonMachineImage machine_image: Machine image intended to be
        used to create the instance from.
        :param str instance_type: AWS EC2 instance type to be created.  E.g.
        "t2.micro".
        """

        self._client = client
        self._machine_image = machine_image
        self._key_pair = None
        self._subnet_id = None
        self._instance_type = instance_type
        self._packages_to_install = []

    def specify_key_pair(self, key_pair):
        """
        Specify the key pair to use with the instance.

        :param KeyPair key_pair: Key pair to be used with the instance.  Assumed
        that it is already created and stored locally.
        :return:
        """

        self._key_pair = key_pair

    def specify_subnet_id(self, subnet_id):
        """
        Specify the subnet id that the instance should be created within.

        :param str subnet_id: The id of the subnet that the instance will be
        created within.
        :return:
        """

        self._subnet_id = subnet_id

    def specify_packages_to_install(self, packages):
        """
        Specify the list of packages to install with cloud-init when the
        instance is created.

        :param List[str] packages: List of package names to be supplied to
        cloud-init.
        :return:
        """

        self._packages_to_install = packages

    def _assemble_user_data(self):
        user_data_lines = ["#cloud-config", ""]

        if self._packages_to_install:
            user_data_lines.append("packages:")

            for single_package in self._packages_to_install:
                line_template = " - {package}"
                package_line = line_template.format(package=single_package)
                user_data_lines.append(package_line)

        joined_user_data = "\n".join(user_data_lines)

        return joined_user_data

    @staticmethod
    def _assemble_tags():
        tags = [
            {
                'Key': 'Project',
                'Value': 'Jobcase-Test-Lab'
            },
            {
                'Key': 'Environment',
                'Value': 'Development'
            }
        ]

        instance_tag_specification = {'ResourceType': 'instance', 'Tags': tags}
        tag_specifications = [instance_tag_specification]

        return tag_specifications

    def create_instance(self):
        """
        Create the EC2 instance on AWS as specified.  Waits until the instance
        is running and then returns.

        :return:
        """

        instance_specification = {
            "InstanceType": self._instance_type,
            "UserData": self._assemble_user_data(),
            "TagSpecifications": self._assemble_tags(),
            "MaxCount": 1,
            "MinCount": 1
        }

        if self._key_pair:
            self._key_pair.add_key_name_to_specification(
                specification=instance_specification
            )

        if self._subnet_id:
            instance_specification['SubnetId'] = self._subnet_id

        self._machine_image.add_image_id_to_specification(
            specification=instance_specification
        )

        response = self._client.run_instances(**instance_specification)
        instance_id = response['Instances'][0]['InstanceId']

        waiter = self._client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        return instance_id


class CreateInstanceScript(object):
    """
    Class that represents the scripting to create an AWS EC2 Instance.  Handles
    the argument parsing as well as the coordination between the different
    objects involved in the process.
    """

    _CONFIG_URL = (
        "https://boto3.readthedocs.io/en/latest/guide/configuration.html"
    )

    def __init__(
            self,
            args,
            exit_strategy,
            operating_system,
            open_strategy,
            aws_library
    ):
        """

        :param List[str] args: Arguments to be parsed.  Should not include the
        name of the script.
        :param exit exit_strategy: The callable used to exit out of the program.
        Should default return an error code.
        :param os operating_system: The object representing the operating
        system.  Should have path and chown methods.
        :param open open_strategy: The callable used to open files for writing.
        :param boto3 aws_library: The module used to create AWS sessions and
        clients.
        """

        self._args = args
        self._exit_strategy = exit_strategy
        self._operating_system = operating_system
        self._open_strategy = open_strategy
        self._aws_library = aws_library

    def _parse_arguments(self):
        argument_parser = argparse.ArgumentParser(
            description="Script to create an AWS EC2 instance."
        )

        argument_parser.add_argument(
            "key_name",
            type=str,
            metavar='key-name',
            help=("Name of the key pair to be created on AWS "
                  "and locally as a pem file.")
        )

        argument_parser.add_argument(
            "-u",
            "--image-is-public",
            action='store_true',
            default=False,
            help="Flags that the image is public."
        )

        argument_parser.add_argument(
            "-i",
            "--image-name",
            type=str,
            default='jobcase-test-app',
            help="Name of the image."
        )

        argument_parser.add_argument(
            "-p",
            "--packages",
            type=list,
            nargs='+',
            default=[
                "httpd",
                "mysql",
                "python",
                "logrotate",
                "aws-cli"
            ],
            help="List of packages to be installed with cloud-init on boot."
        )

        argument_parser.add_argument(
            '-t',
            '--instance-type',
            type=str,
            default='t2.micro',
            help="EC2 instance type to be created."
        )

        argument_parser.add_argument(
            '-r',
            '--region-name',
            type=str,
            default='us-east-1',
            help="Region to create the instance in."
        )

        argument_parser.add_argument(
            '-s',
            '--subnet-id',
            type=str,
            help="Subnet to create the instance in."
        )

        parsed_arguments = argument_parser.parse_args(args=self._args)

        return parsed_arguments

    def _execute_creation_and_communicate(self, ec2_instance, key_pair):
        ec2_instance.specify_key_pair(key_pair=key_pair)

        try:
            key_pair.create_in_all_locations()
        except KeyExistsError as key_error:
            error_message = str(key_error)
            self._exit_with_error(message=error_message)

        try:
            instance_id = ec2_instance.create_instance()
            success_template = "{instance_id} created successfully."
            success_message = success_template.format(instance_id=instance_id)
            print(success_message)

        except ImageMissingError as image_missing_error:
            error_message = str(image_missing_error)
            self._exit_with_error(message=error_message)

    # noinspection PyUnresolvedReferences
    def _create_key_and_instance(self, parsed_arguments, client):
        key_pair = KeyPair(
            key_name=parsed_arguments.key_name,
            client=client,
            operating_system=self._operating_system,
            open_strategy=self._open_strategy
        )

        image = AmazonMachineImage(
            client=client,
            name=parsed_arguments.image_name,
            is_public=parsed_arguments.image_is_public
        )

        ec2_instance = InstanceBuilder(
            client=client,
            machine_image=image,
            instance_type=parsed_arguments.instance_type
        )

        ec2_instance.specify_subnet_id(subnet_id=parsed_arguments.subnet_id)
        ec2_instance.specify_packages_to_install(
            packages=parsed_arguments.packages
        )

        self._execute_creation_and_communicate(
            ec2_instance=ec2_instance,
            key_pair=key_pair
        )

    def _exit_with_error_and_config(self, message):
        config_template = "{error_message}. See {config_url}"
        config_error_message = config_template.format(
            error_message=message,
            config_url=self._CONFIG_URL
        )

        self._exit_with_error(message=config_error_message)

    def _exit_with_error(self, message):
        error_template = "{error_message}. Exiting."
        exit_message = error_template.format(error_message=message)

        self._exit_strategy(exit_message)

    def _create_session(self, parsed_arguments):
        session = self._aws_library.session.Session(
            region_name=parsed_arguments.region_name
        )

        if not session.get_credentials():
            error_message = "Could not locate any credentials"
            self._exit_with_error_and_config(message=error_message)

        return session

    # noinspection PyUnresolvedReferences
    def _create_client(self, parsed_arguments):
        session = self._create_session(parsed_arguments=parsed_arguments)

        try:
            client = session.client('ec2')

            return client

        except exceptions.NoRegionError:
            error_message = "Could not locate a default region"
            self._exit_with_error_and_config(message=error_message)

    def run(self):
        """
        Call to execute the script.  Will parse arguments, create a client,
        create a key pair, and then create an instance.  Exits from the program
        if an error is encountered.
        :return:
        """

        parsed_arguments = self._parse_arguments()
        client = self._create_client(parsed_arguments=parsed_arguments)
        self._create_key_and_instance(
            parsed_arguments=parsed_arguments,
            client=client
        )


if __name__ == '__main__':
    script = CreateInstanceScript(
        args=sys.argv[1:],
        exit_strategy=exit,
        operating_system=os,
        open_strategy=open,
        aws_library=boto3
    )

    script.run()
