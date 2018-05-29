import pytest
import time
from datetime import datetime, timedelta

from cfme import test_requirements
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.tier(3),
    test_requirements.c_and_u,
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([VMwareProvider],
    required_fields=[(['cap_and_util', 'capandu_vm'], 'cu-24x7')])
]

ELEMENTS = ['vm', 'host']
GRAPH_TYPE = ['hourly', 'daily']


@pytest.fixture(params=ELEMENTS)
def element(appliance, provider, request):
    if request.param == 'host':
        collection = appliance.collections.hosts
        for test_host in provider.data['hosts']:
            if not test_host.get('test_fleece', False):
                continue
            ele = collection.instantiate(name=test_host.name, provider=provider)
    elif request.param == 'vm':
        collection = appliance.provider_based_collection(provider)
        ele = collection.instantiate('cu-24x7', provider)
    yield ele


def run_once(f):
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)
    wrapper.has_run = False
    return wrapper


@run_once
def order_data(appliance, start_date=None, end_date=None, back_days=None):
    view = navigate_to(appliance.server.zone, 'CANDUGapCollection')

    if back_days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=back_days)
    else:
        ValueError("start and end date required")

    view.candugapcollection.start_date.fill(start_date)
    view.candugapcollection.end_date.fill(end_date)
    view.candugapcollection.submit.click()
    time.sleep(15 * 60)


@pytest.mark.parametrize('graph_type', GRAPH_TYPE)
def test_gap_collection(appliance, provider, graph_type, enable_candu, element):
    """ Test gap collection data

    prerequisites:
        * C&U enabled appliance

    Steps:
        * Navigate to Configuration > Diagnostics > Zone Gap Collection Page
        * Order old data (2 days back)
        * Navigate to VM or Host Utilization page
        * Check for Hourly data
        * Check for Daily data
    """
    # order 2 days back data for test
    dates = [datetime.now() - timedelta(days=x) for x in range(1, 3)]
    end_date, start_date = dates
    order_data(appliance, start_date=start_date, end_date=end_date)

    element.wait_candu_data_available(timeout=1200)

    view = navigate_to(element, 'candu')
    view.options.interval.fill(graph_type.capitalize())
    try:
        graph = getattr(view, 'vm_cpu')
    except AttributeError:
        graph = getattr(view.interval_type, 'host_cpu')
    assert graph.is_displayed

    def refresh():
        provider.browser.refresh()
        view = navigate_to(element, 'candu')
        view.options.interval.fill(graph_type.capitalize())

    # wait, some time graph took time to load
    wait_for(lambda: len(graph.all_legends) > 0,
             delay=5, timeout=600, fail_func=refresh)

    # check old data collection started or not
    for date in dates:
        view.options.calendar.fill(date)
        graph_data = 0
        for leg in graph.all_legends:
            graph.display_legends(leg)
            for data in graph.data_for_legends(leg).values():
                graph_data += float(data[leg].replace(',', '').replace('%', '').split()[0])
        assert graph_data > 0
