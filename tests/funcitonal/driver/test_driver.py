from scrapli_netconf.response import NetconfResponse

from ...helper import xmldiffs
from ...test_data.devices import CONFIG_REPLACER, INPUTS_OUTPUTS


def test_get_filter_subtree(sync_conn):
    conn = sync_conn[0]
    device_type = sync_conn[1]
    conn.open()

    # TODO juniper and iosxe
    if device_type != "cisco_iosxr":
        return

    expected_config_elements = INPUTS_OUTPUTS[device_type].GET_SUBTREE_ELEMENTS
    expected_result = INPUTS_OUTPUTS[device_type].GET_SUBTREE_RESULT
    filter_ = INPUTS_OUTPUTS[device_type].GET_SUBTREE_FILTER

    response = conn.get(filter_=filter_, filter_type="subtree")

    assert isinstance(response, NetconfResponse)
    assert response.failed is False
    assert all(
        elem in list(response.get_xml_elements().keys()) for elem in expected_config_elements
    )
    assert not xmldiffs(response.result, expected_result)


# def test_get_filter_xpath(sync_conn):
#     # TODO do any of these platforms actually support xpath?
#     pass


def test_get_config(sync_conn):
    conn = sync_conn[0]
    device_type = sync_conn[1]
    conn.open()

    config_replacer = CONFIG_REPLACER[device_type]
    expected_config_elements = INPUTS_OUTPUTS[device_type].FULL_GET_CONFIG_ELEMENTS
    expected_result = INPUTS_OUTPUTS[device_type].FULL_GET_CONFIG_RESULT

    response = conn.get_config()

    assert isinstance(response, NetconfResponse)
    assert response.failed is False
    assert all(
        elem in list(response.get_xml_elements().keys()) for elem in expected_config_elements
    )
    assert not xmldiffs(config_replacer(response.result), expected_result)


def test_get_config_filtered_single_filter_subtree(sync_conn):
    conn = sync_conn[0]
    device_type = sync_conn[1]
    conn.open()

    config_replacer = CONFIG_REPLACER[device_type]
    expected_config_elements = INPUTS_OUTPUTS[device_type].CONFIG_FILTER_SINGLE_GET_CONFIG_ELEMENTS
    filters = INPUTS_OUTPUTS[device_type].CONFIG_FILTER_SINGLE
    expected_result = INPUTS_OUTPUTS[device_type].CONFIG_FILTER_SINGLE_GET_CONFIG_RESULT

    response = conn.get_config(filters=filters, filter_type="subtree")

    assert isinstance(response, NetconfResponse)
    assert response.failed is False
    assert all(
        elem in list(response.get_xml_elements().keys()) for elem in expected_config_elements
    )
    assert not xmldiffs(config_replacer(response.result), expected_result)


def test_get_config_filtered_multi_filter_subtree(sync_conn):
    conn = sync_conn[0]
    device_type = sync_conn[1]
    conn.open()

    # TODO juniper and iosxe
    if device_type != "cisco_iosxr":
        return

    config_replacer = CONFIG_REPLACER[device_type]
    expected_config_elements = INPUTS_OUTPUTS[device_type].CONFIG_FILTER_MULTI_GET_CONFIG_ELEMENTS
    filters = INPUTS_OUTPUTS[device_type].CONFIG_FILTER_MULTI
    expected_result = INPUTS_OUTPUTS[device_type].CONFIG_FILTER_MULTI_GET_CONFIG_RESULT

    response = conn.get_config(filters=filters, filter_type="subtree")

    assert isinstance(response, NetconfResponse)
    assert response.failed is False
    assert all(
        elem in list(response.get_xml_elements().keys()) for elem in expected_config_elements
    )
    assert not xmldiffs(config_replacer(response.result), expected_result)


# def test_get_config_filter_single_filter_xpath(sync_conn):
#     # TODO do any of these platforms actually support xpath?
#     pass


# def test_get_config_filter_multi_filter_xpath(sync_conn):
#     # TODO do any of these platforms actually support xpath?
#     pass


# def test_edit_config(sync_conn):
#     pass


# def test_commit(sync_conn):
#     pass


# def test_discard(sync_conn):
#     pass


def test_lock_unlock(sync_conn):
    conn = sync_conn[0]
    device_type = sync_conn[1]

    # stripping namespaces for this check because we dont really care that much about them here
    conn.strip_namespaces = True
    conn.open()

    target = "candidate"
    if device_type == "cisco_iosxe":
        target = "running"

    response = conn.lock(target=target)
    assert isinstance(response, NetconfResponse)
    assert response.failed is False
    assert not xmldiffs(response.result, """<rpc-reply message-id="101"><ok/></rpc-reply>""")

    response = conn.unlock(target=target)
    assert isinstance(response, NetconfResponse)
    assert response.failed is False
    assert not xmldiffs(response.result, """<rpc-reply message-id="102"><ok/></rpc-reply>""")


# def test_rpc(sync_conn):
#     pass