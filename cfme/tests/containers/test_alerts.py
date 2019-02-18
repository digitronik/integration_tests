import pytest

from cfme.containers.provider import ContainersProvider


pytestmark = [
    pytest.mark.provider(classes=[ContainersProvider], required_flags=['prometheus_alerts'])
]

# TODO There needs to be more to this test


def test_add_alerts_provider(provider):
    """
    Polarion:
        assignee: juwatts
        initialEstimate: 1/4h
        caseimportance: low
        casecomponent: Containers
    """
    provider.setup()
