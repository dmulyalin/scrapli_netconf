<link rel="preload stylesheet" as="style" href="https://cdnjs.cloudflare.com/ajax/libs/10up-sanitize.css/11.0.1/sanitize.min.css" integrity="sha256-PK9q560IAAa6WVRRh76LtCaI8pjTJ2z11v0miyNNjrs=" crossorigin>
<link rel="preload stylesheet" as="style" href="https://cdnjs.cloudflare.com/ajax/libs/10up-sanitize.css/11.0.1/typography.min.css" integrity="sha256-7l/o7C8jubJiy74VsKTidCy1yBkRtiUGbVkYBylBqUg=" crossorigin>
<link rel="stylesheet preload" as="style" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/10.1.1/styles/github.min.css" crossorigin>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/10.1.1/highlight.min.js" integrity="sha256-Uv3H6lx7dJmRfRvH8TH6kJD1TSK1aFcwgx+mdg3epi8=" crossorigin></script>
<script>window.addEventListener('DOMContentLoaded', () => hljs.initHighlighting())</script>















#Module scrapli_netconf.driver.base_driver

scrapli_netconf.driver.base_driver

<details class="source">
    <summary>
        <span>Expand source code</span>
    </summary>
    <pre>
        <code class="python">
# pylint: disable=C0302
"""scrapli_netconf.driver.base_driver"""
import importlib
from dataclasses import fields
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple, Union

from lxml import etree
from lxml.etree import _Element

from scrapli.driver.base.base_driver import BaseDriver
from scrapli.exceptions import ScrapliTypeError, ScrapliValueError
from scrapli.helper import user_warning
from scrapli_netconf.channel.base_channel import NetconfBaseChannelArgs
from scrapli_netconf.constants import NetconfClientCapabilities, NetconfVersion, XmlParserVersion
from scrapli_netconf.exceptions import CapabilityNotSupported
from scrapli_netconf.response import NetconfResponse

COMPRESSED_PARSER = etree.XMLParser(remove_blank_text=True, recover=True)
STANDARD_PARSER = etree.XMLParser(remove_blank_text=False, recover=True)


class NetconfBaseOperations(Enum):
    FILTER_SUBTREE = "<filter type='{filter_type}'></filter>"
    FILTER_XPATH = "<filter type='{filter_type}' select='{xpath}'></filter>"
    WITH_DEFAULTS_SUBTREE = (
        "<with-defaults xmlns='urn:ietf:params:xml:ns:yang:ietf-netconf-with-defaults'>"
        "{default_type}</with-defaults>"
    )
    GET = "<get></get>"
    GET_CONFIG = "<get-config><source><{source}/></source></get-config>"
    EDIT_CONFIG = "<edit-config><target><{target}/></target></edit-config>"
    DELETE_CONFIG = "<delete-config><target><{target}/></target></delete-config>"
    COPY_CONFIG = (
        "<copy-config><target><{target}/></target><source><{source}/></source></copy-config>"
    )
    COMMIT = "<commit/>"
    DISCARD = "<discard-changes/>"
    LOCK = "<lock><target><{target}/></target></lock>"
    UNLOCK = "<unlock><target><{target}/></target></unlock>"
    RPC = "<rpc xmlns='urn:ietf:params:xml:ns:netconf:base:1.0' message-id='{message_id}'></rpc>"
    VALIDATE = "<validate><source><{source}/></source></validate>"


class NetconfBaseDriver(BaseDriver):
    host: str
    readable_datastores: List[str]
    writeable_datastores: List[str]
    strip_namespaces: bool
    strict_datastores: bool
    flatten_input: bool
    _netconf_base_channel_args: NetconfBaseChannelArgs

    @property
    def netconf_version(self) -> NetconfVersion:
        """
        Getter for 'netconf_version' attribute

        Args:
            N/A

        Returns:
            NetconfVersion: netconf_version enum

        Raises:
            N/A

        """
        return self._netconf_base_channel_args.netconf_version

    @netconf_version.setter
    def netconf_version(self, value: NetconfVersion) -> None:
        """
        Setter for 'netconf_version' attribute

        Args:
            value: NetconfVersion

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type NetconfVersion

        """
        if not isinstance(value, NetconfVersion):
            raise ScrapliTypeError

        self.logger.debug(f"setting 'netconf_version' value to '{value.value}'")

        self._netconf_base_channel_args.netconf_version = value

        if self._netconf_base_channel_args.netconf_version == NetconfVersion.VERSION_1_0:
            self._base_channel_args.comms_prompt_pattern = "]]>]]>"
        else:
            self._base_channel_args.comms_prompt_pattern = r"^##$"

    @property
    def client_capabilities(self) -> NetconfClientCapabilities:
        """
        Getter for 'client_capabilities' attribute

        Args:
            N/A

        Returns:
            NetconfClientCapabilities: netconf client capabilities enum

        Raises:
            N/A

        """
        return self._netconf_base_channel_args.client_capabilities

    @client_capabilities.setter
    def client_capabilities(self, value: NetconfClientCapabilities) -> None:
        """
        Setter for 'client_capabilities' attribute

        Args:
            value: NetconfClientCapabilities value for client_capabilities

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type NetconfClientCapabilities

        """
        if not isinstance(value, NetconfClientCapabilities):
            raise ScrapliTypeError

        self.logger.debug(f"setting 'client_capabilities' value to '{value.value}'")

        self._netconf_base_channel_args.client_capabilities = value

    @property
    def server_capabilities(self) -> List[str]:
        """
        Getter for 'server_capabilities' attribute

        Args:
            N/A

        Returns:
            list: list of strings of server capabilities

        Raises:
            N/A

        """
        return self._netconf_base_channel_args.server_capabilities or []

    @server_capabilities.setter
    def server_capabilities(self, value: NetconfClientCapabilities) -> None:
        """
        Setter for 'server_capabilities' attribute

        Args:
            value: list of strings of netconf server capabilities

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type list

        """
        if not isinstance(value, list):
            raise ScrapliTypeError

        self.logger.debug(f"setting 'server_capabilities' value to '{value}'")

        self._netconf_base_channel_args.server_capabilities = value

    @staticmethod
    def _determine_preferred_netconf_version(
        preferred_netconf_version: Optional[str],
    ) -> NetconfVersion:
        """
        Determine users preferred netconf version (if applicable)

        Args:
            preferred_netconf_version: optional string indicating users preferred netconf version

        Returns:
            NetconfVersion: users preferred netconf version

        Raises:
            ScrapliValueError: if preferred_netconf_version is not None or a valid option

        """
        if preferred_netconf_version is None:
            return NetconfVersion.UNKNOWN
        if preferred_netconf_version == "1.0":
            return NetconfVersion.VERSION_1_0
        if preferred_netconf_version == "1.1":
            return NetconfVersion.VERSION_1_1

        raise ScrapliValueError(
            "'preferred_netconf_version' provided with invalid value, must be one of: "
            "None, '1.0', or '1.1'"
        )

    @staticmethod
    def _determine_preferred_xml_parser(use_compressed_parser: bool) -> XmlParserVersion:
        """
        Determine users preferred xml payload parser

        Args:
            use_compressed_parser: bool indicating use of compressed parser or not

        Returns:
            XmlParserVersion: users xml parser version

        Raises:
            N/A

        """
        if use_compressed_parser is True:
            return XmlParserVersion.COMPRESSED_PARSER
        return XmlParserVersion.STANDARD_PARSER

    @property
    def xml_parser(self) -> etree.XMLParser:
        """
        Getter for 'xml_parser' attribute

        Args:
            N/A

        Returns:
            etree.XMLParser: parser to use for parsing xml documents

        Raises:
            N/A

        """
        if self._netconf_base_channel_args.xml_parser == XmlParserVersion.COMPRESSED_PARSER:
            return COMPRESSED_PARSER
        return STANDARD_PARSER

    @xml_parser.setter
    def xml_parser(self, value: XmlParserVersion) -> None:
        """
        Setter for 'xml_parser' attribute

        Args:
            value: enum indicating parser version to use

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type XmlParserVersion

        """
        if not isinstance(value, XmlParserVersion):
            raise ScrapliTypeError

        self._netconf_base_channel_args.xml_parser = value

    def _transport_factory(self) -> Tuple[Callable[..., Any], object]:
        """
        Determine proper transport class and necessary arguments to initialize that class

        Args:
            N/A

        Returns:
            Tuple[Callable[..., Any], object]: tuple of transport class and dataclass of transport
                class specific arguments

        Raises:
            N/A

        """
        transport_plugin_module = importlib.import_module(
            f"scrapli_netconf.transport.plugins.{self.transport_name}.transport"
        )

        transport_class = getattr(
            transport_plugin_module, f"Netconf{self.transport_name.capitalize()}Transport"
        )
        plugin_transport_args_class = getattr(transport_plugin_module, "PluginTransportArgs")

        _plugin_transport_args = {
            field.name: getattr(self, field.name) for field in fields(plugin_transport_args_class)
        }

        plugin_transport_args = plugin_transport_args_class(**_plugin_transport_args)

        return transport_class, plugin_transport_args

    def _build_readable_datastores(self) -> None:
        """
        Build a list of readable datastores based on server's advertised capabilities

        Args:
            N/A

        Returns:
            None

        Raises:
            N/A

        """
        self.readable_datastores = []
        self.readable_datastores.append("running")
        if "urn:ietf:params:netconf:capability:candidate:1.0" in self.server_capabilities:
            self.readable_datastores.append("candidate")
        if "urn:ietf:params:netconf:capability:startup:1.0" in self.server_capabilities:
            self.readable_datastores.append("startup")

    def _build_writeable_datastores(self) -> None:
        """
        Build a list of writeable/editable datastores based on server's advertised capabilities

        Args:
            N/A

        Returns:
            None

        Raises:
            N/A

        """
        self.writeable_datastores = []
        if "urn:ietf:params:netconf:capability:writeable-running:1.0" in self.server_capabilities:
            self.writeable_datastores.append("running")
        if "urn:ietf:params:netconf:capability:writable-running:1.0" in self.server_capabilities:
            # NOTE: iosxe shows "writable" (as of 2020.07.01) despite RFC being "writeable"
            self.writeable_datastores.append("running")
        if "urn:ietf:params:netconf:capability:candidate:1.0" in self.server_capabilities:
            self.writeable_datastores.append("candidate")
        if "urn:ietf:params:netconf:capability:startup:1.0" in self.server_capabilities:
            self.writeable_datastores.append("startup")

    def _validate_get_config_target(self, source: str) -> None:
        """
        Validate get-config source is acceptable

        Args:
            source: configuration source to get; typically one of running|startup|candidate

        Returns:
            None

        Raises:
            ScrapliValueError: if an invalid source was selected and strict_datastores is True

        """
        if source not in self.readable_datastores:
            msg = f"'source' should be one of {self.readable_datastores}, got '{source}'"
            self.logger.warning(msg)
            if self.strict_datastores is True:
                raise ScrapliValueError(msg)
            user_warning(title="Invalid datastore source!", message=msg)

    def _validate_edit_config_target(self, target: str) -> None:
        """
        Validate edit-config/lock/unlock target is acceptable

        Args:
            target: configuration source to edit/lock; typically one of running|startup|candidate

        Returns:
            None

        Raises:
            ScrapliValueError: if an invalid source was selected

        """
        if target not in self.writeable_datastores:
            msg = f"'target' should be one of {self.writeable_datastores}, got '{target}'"
            self.logger.warning(msg)
            if self.strict_datastores is True:
                raise ScrapliValueError(msg)
            user_warning(title="Invalid datastore target!", message=msg)

    def _validate_delete_config_target(self, target: str) -> None:
        """
        Validate delete-config/lock/unlock target is acceptable

        Args:
            target: configuration source to delete; typically one of startup|candidate

        Returns:
            None

        Raises:
            ScrapliValueError: if an invalid target was selected

        """
        if target == "running" or target not in self.writeable_datastores:
            msg = f"'target' should be one of {self.writeable_datastores}, got '{target}'"
            if target == "running":
                msg = "delete-config 'target' may not be 'running'"
            self.logger.warning(msg)
            if self.strict_datastores is True:
                raise ScrapliValueError(msg)
            user_warning(title="Invalid datastore target!", message=msg)

    def _build_base_elem(self) -> _Element:
        """
        Create base element for netconf operations

        Args:
            N/A

        Returns:
            _Element: lxml base element to use for netconf operation

        Raises:
            N/A

        """
        # pylint did not seem to want to be ok with assigning this as a class attribute... and its
        # only used here so... here we are
        self.message_id: int  # pylint: disable=W0201
        self.logger.debug(f"Building base element for message id {self.message_id}")
        base_xml_str = NetconfBaseOperations.RPC.value.format(message_id=self.message_id)
        self.message_id += 1
        base_elem = etree.fromstring(text=base_xml_str)
        return base_elem

    def _build_filter(self, filter_: str, filter_type: str = "subtree") -> _Element:
        """
        Create filter element for a given rpc

        The `filter_` string may contain multiple xml elements at its "root" (subtree filters); we
        will simply place the payload into a temporary "tmp" outer tag so that when we cast it to an
        etree object the elements are all preserved; without this outer "tmp" tag, lxml will scoop
        up only the first element provided as it appears to be the root of the document presumably.

        An example valid (to scrapli netconf at least) xml filter would be:

        ```
        <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
            <interface-configuration>
                <active>act</active>
            </interface-configuration>
        </interface-configurations>
        <netconf-yang xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-man-netconf-cfg">
        </netconf-yang>
        ```

        Args:
            filter_: strings of filters to build into a filter element or (for subtree) a full
                filter string (in filter tags)
            filter_type: type of filter; subtree|xpath

        Returns:
            _Element: lxml filter element to use for netconf operation

        Raises:
            CapabilityNotSupported: if xpath selected and not supported on server
            ScrapliValueError: if filter_type is not one of subtree|xpath

        """
        if filter_type == "subtree":
            # tmp tags to place the users kinda not valid xml filter into
            _filter_ = f"<tmp>{filter_}</tmp>"
            # "validate" subtree filter by forcing it into xml, parser "flattens" it as well
            tmp_xml_filter_element = etree.fromstring(_filter_, parser=self.xml_parser)

            if tmp_xml_filter_element.getchildren()[0].tag == "filter":
                # if the user filter was already wrapped in filter tags we'll end up here, we will
                # blindly reuse the users filter but we'll make sure that the filter "type" is set
                xml_filter_elem = tmp_xml_filter_element.getchildren()[0]
                xml_filter_elem.attrib["type"] = "subtree"
            else:
                xml_filter_elem = etree.fromstring(
                    NetconfBaseOperations.FILTER_SUBTREE.value.format(filter_type=filter_type),
                )

                # iterate through the children inside the tmp tags and insert *those* elements into
                # the actual final filter payload
                for xml_filter_element in tmp_xml_filter_element:
                    # insert the subtree filter into the parent filter element
                    xml_filter_elem.insert(1, xml_filter_element)

        elif filter_type == "xpath":
            if "urn:ietf:params:netconf:capability:xpath:1.0" not in self.server_capabilities:
                msg = "xpath filter requested, but is not supported by the server"
                self.logger.exception(msg)
                raise CapabilityNotSupported(msg)
            xml_filter_elem = etree.fromstring(
                NetconfBaseOperations.FILTER_XPATH.value.format(
                    filter_type=filter_type, xpath=filter_
                ),
                parser=self.xml_parser,
            )
        else:
            raise ScrapliValueError(
                f"'filter_type' should be one of subtree|xpath, got '{filter_type}'"
            )
        return xml_filter_elem

    def _build_with_defaults(self, default_type: str = "report-all") -> _Element:
        """
        Create with-defaults element for a given operation

        Args:
            default_type: enumeration of with-defaults; report-all|trim|explicit|report-all-tagged

        Returns:
            _Element: lxml with-defaults element to use for netconf operation

        Raises:
            CapabilityNotSupported: if default_type provided but not supported by device
            ScrapliValueError: if default_type is not one of
                report-all|trim|explicit|report-all-tagged

        """

        if default_type in ["report-all", "trim", "explicit", "report-all-tagged"]:
            if (
                "urn:ietf:params:netconf:capability:with-defaults:1.0"
                not in self.server_capabilities
            ):
                msg = "with-defaults requested, but is not supported by the server"
                self.logger.exception(msg)
                raise CapabilityNotSupported(msg)
            xml_with_defaults_element = etree.fromstring(
                NetconfBaseOperations.WITH_DEFAULTS_SUBTREE.value.format(default_type=default_type),
                parser=self.xml_parser,
            )
        else:
            raise ScrapliValueError(
                "'default_type' should be one of report-all|trim|explicit|report-all-tagged, "
                f"got '{default_type}'"
            )
        return xml_with_defaults_element

    def _finalize_channel_input(self, xml_request: _Element) -> bytes:
        """
        Create finalized channel input (as bytes)

        Args:
            xml_request: finalized xml element to cast to bytes and add declaration to

        Returns:
            bytes: finalized bytes input -- with 1.0 delimiter or 1.1 encoding

        Raises:
            N/A

        """
        channel_input: bytes = etree.tostring(
            element_or_tree=xml_request, xml_declaration=True, encoding="utf-8"
        )

        if self.netconf_version == NetconfVersion.VERSION_1_0:
            channel_input = channel_input + b"]]>]]>"
        else:
            # format message for chunk (netconf 1.1) style message
            channel_input = b"#%b\n" % str(len(channel_input)).encode() + channel_input + b"\n##"

        return channel_input

    def _pre_get(self, filter_: str, filter_type: str = "subtree") -> NetconfResponse:
        """
        Handle pre "get" tasks for consistency between sync/async versions

        *NOTE*
        The channel input (filter_) is loaded up as an lxml etree element here, this is done with a
        parser that removes whitespace. This has a somewhat undesirable effect of making any
        "pretty" input not pretty, however... after we load the xml object (which we do to validate
        that it is valid xml) we dump that xml object back to a string to be used as the actual
        raw payload we send down the channel, which means we are sending "flattened" (not pretty/
        indented xml) to the device. This is important it seems! Some devices seme to not mind
        having the "nicely" formatted input (pretty xml). But! On devices that "echo" the inputs
        back -- sometimes the device will respond to our rpc without "finishing" echoing our inputs
        to the device, this breaks the core "read until input" processing that scrapli always does.
        For whatever reason if there are no line breaks this does not seem to happen? /shrug. Note
        that this comment applies to all of the "pre" methods that we parse a filter/payload!

        Args:
            filter_: string filter to apply to the get
            filter_type: type of filter; subtree|xpath

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(
            f"Building payload for 'get' operation. filter_type: {filter_type}, filter_: {filter_}"
        )

        # build base request and insert the get element
        xml_request = self._build_base_elem()
        xml_get_element = etree.fromstring(NetconfBaseOperations.GET.value)
        xml_request.insert(0, xml_get_element)

        # build filter element
        xml_filter_elem = self._build_filter(filter_=filter_, filter_type=filter_type)

        # insert filter element into parent get element
        get_element = xml_request.find("get")
        get_element.insert(0, xml_filter_elem)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(f"Built payload for 'get' operation. Payload: {channel_input.decode()}")
        return response

    def _pre_get_config(
        self,
        source: str = "running",
        filter_: Optional[str] = None,
        filter_type: str = "subtree",
        default_type: Optional[str] = None,
    ) -> NetconfResponse:
        """
        Handle pre "get_config" tasks for consistency between sync/async versions

        Args:
            source: configuration source to get; typically one of running|startup|candidate
            filter_: string of filter(s) to apply to configuration
            filter_type: type of filter; subtree|xpath
            default_type: string of with-default mode to apply when retrieving configuration

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(
            f"Building payload for 'get-config' operation. source: {source}, filter_type: "
            f"{filter_type}, filter: {filter_}, default_type: {default_type}"
        )
        self._validate_get_config_target(source=source)

        # build base request and insert the get-config element
        xml_request = self._build_base_elem()
        xml_get_config_element = etree.fromstring(
            NetconfBaseOperations.GET_CONFIG.value.format(source=source), parser=self.xml_parser
        )
        xml_request.insert(0, xml_get_config_element)

        if filter_ is not None:
            xml_filter_elem = self._build_filter(filter_=filter_, filter_type=filter_type)
            # insert filter element into parent get element
            get_element = xml_request.find("get-config")
            # insert *after* source, otherwise juniper seems to gripe, maybe/probably others as well
            get_element.insert(1, xml_filter_elem)

        if default_type is not None:
            xml_with_defaults_elem = self._build_with_defaults(default_type=default_type)
            get_element = xml_request.find("get-config")
            get_element.insert(2, xml_with_defaults_elem)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'get-config' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_edit_config(self, config: str, target: str = "running") -> NetconfResponse:
        """
        Handle pre "edit_config" tasks for consistency between sync/async versions

        Args:
            config: configuration to send to device
            target: configuration source to target; running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(
            f"Building payload for 'edit-config' operation. target: {target}, config: {config}"
        )
        self._validate_edit_config_target(target=target)

        xml_config = etree.fromstring(config, parser=self.xml_parser)

        # build base request and insert the edit-config element
        xml_request = self._build_base_elem()
        xml_edit_config_element = etree.fromstring(
            NetconfBaseOperations.EDIT_CONFIG.value.format(target=target)
        )
        xml_request.insert(0, xml_edit_config_element)

        # insert parent filter element to first position so that target stays first just for nice
        # output/readability
        edit_config_element = xml_request.find("edit-config")
        edit_config_element.insert(1, xml_config)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'edit-config' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_delete_config(self, target: str = "running") -> NetconfResponse:
        """
        Handle pre "edit_config" tasks for consistency between sync/async versions

        Args:
            target: configuration source to target; startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(f"Building payload for 'delete-config' operation. target: {target}")
        self._validate_delete_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_validate_element = etree.fromstring(
            NetconfBaseOperations.DELETE_CONFIG.value.format(target=target), parser=self.xml_parser
        )
        xml_request.insert(0, xml_validate_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'delete-config' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_commit(self) -> NetconfResponse:
        """
        Handle pre "commit" tasks for consistency between sync/async versions

        Args:
            N/A

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'commit' operation")
        xml_request = self._build_base_elem()
        xml_commit_element = etree.fromstring(
            NetconfBaseOperations.COMMIT.value, parser=self.xml_parser
        )
        xml_request.insert(0, xml_commit_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'commit' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_discard(self) -> NetconfResponse:
        """
        Handle pre "discard" tasks for consistency between sync/async versions

        Args:
            N/A

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'discard' operation.")
        xml_request = self._build_base_elem()
        xml_commit_element = etree.fromstring(
            NetconfBaseOperations.DISCARD.value, parser=self.xml_parser
        )
        xml_request.insert(0, xml_commit_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'discard' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_lock(self, target: str) -> NetconfResponse:
        """
        Handle pre "lock" tasks for consistency between sync/async versions

        Args:
            target: configuration source to target; running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'lock' operation.")
        self._validate_edit_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_lock_element = etree.fromstring(
            NetconfBaseOperations.LOCK.value.format(target=target), parser=self.xml_parser
        )
        xml_request.insert(0, xml_lock_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(f"Built payload for 'lock' operation. Payload: {channel_input.decode()}")
        return response

    def _pre_unlock(self, target: str) -> NetconfResponse:
        """
        Handle pre "unlock" tasks for consistency between sync/async versions

        Args:
            target: configuration source to target; running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'unlock' operation.")
        self._validate_edit_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_lock_element = etree.fromstring(
            NetconfBaseOperations.UNLOCK.value.format(target=target, parser=self.xml_parser)
        )
        xml_request.insert(0, xml_lock_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'unlock' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_rpc(self, filter_: Union[str, _Element]) -> NetconfResponse:
        """
        Handle pre "rpc" tasks for consistency between sync/async versions

        Args:
            filter_: filter/rpc to execute

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'rpc' operation.")
        xml_request = self._build_base_elem()

        # build filter element
        if isinstance(filter_, str):
            xml_filter_elem = etree.fromstring(filter_, parser=self.xml_parser)
        else:
            xml_filter_elem = filter_

        # insert filter element
        xml_request.insert(0, xml_filter_elem)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(f"Built payload for 'rpc' operation. Payload: {channel_input.decode()}")
        return response

    def _pre_validate(self, source: str) -> NetconfResponse:
        """
        Handle pre "validate" tasks for consistency between sync/async versions

        Args:
            source: configuration source to validate; typically one of running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            CapabilityNotSupported: if 'validate' capability does not exist

        """
        self.logger.debug("Building payload for 'validate' operation.")

        if not any(
            cap in self.server_capabilities
            for cap in (
                "urn:ietf:params:netconf:capability:validate:1.0",
                "urn:ietf:params:netconf:capability:validate:1.1",
            )
        ):
            msg = "validate requested, but is not supported by the server"
            self.logger.exception(msg)
            raise CapabilityNotSupported(msg)

        self._validate_edit_config_target(target=source)

        xml_request = self._build_base_elem()
        xml_validate_element = etree.fromstring(
            NetconfBaseOperations.VALIDATE.value.format(source=source), parser=self.xml_parser
        )
        xml_request.insert(0, xml_validate_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'validate' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_copy_config(self, source: str, target: str) -> NetconfResponse:
        """
        Handle pre "copy_config" tasks for consistency between sync/async versions

        Note that source is not validated/checked since it could be a url or a full configuration
        element itself.

        Args:
            source: configuration, url, or datastore to copy into the target datastore
            target: copy config destination/target; typically one of running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'copy_config' operation.")

        self._validate_edit_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_validate_element = etree.fromstring(
            NetconfBaseOperations.COPY_CONFIG.value.format(source=source, target=target),
            parser=self.xml_parser,
        )
        xml_request.insert(0, xml_validate_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'copy-config' operation. Payload: {channel_input.decode()}"
        )
        return response
        </code>
    </pre>
</details>




## Classes

### NetconfBaseDriver


```text
BaseDriver Object

BaseDriver is the root for all Scrapli driver classes. The synchronous and asyncio driver
base driver classes can be used to provide a semi-pexpect like experience over top of
whatever transport a user prefers. Generally, however, the base driver classes should not be
used directly. It is best to use the GenericDriver (or AsyncGenericDriver) or NetworkDriver
(or AsyncNetworkDriver) sub-classes of the base drivers.

Args:
    host: host ip/name to connect to
    port: port to connect to
    auth_username: username for authentication
    auth_private_key: path to private key for authentication
    auth_private_key_passphrase: passphrase for decrypting ssh key if necessary
    auth_password: password for authentication
    auth_strict_key: strict host checking or not
    auth_bypass: bypass "in channel" authentication -- only supported with telnet,
        asynctelnet, and system transport plugins
    timeout_socket: timeout for establishing socket/initial connection in seconds
    timeout_transport: timeout for ssh|telnet transport in seconds
    timeout_ops: timeout for ssh channel operations
    comms_prompt_pattern: raw string regex pattern -- preferably use `^` and `$` anchors!
        this is the single most important attribute here! if this does not match a prompt,
        scrapli will not work!
        IMPORTANT: regex search uses multi-line + case insensitive flags. multi-line allows
        for highly reliably matching for prompts however we do NOT strip trailing whitespace
        for each line, so be sure to add '\\s?' or similar if your device needs that. This
        should be mostly sorted for you if using network drivers (i.e. `IOSXEDriver`).
        Lastly, the case insensitive is just a convenience factor so i can be lazy.
    comms_return_char: character to use to send returns to host
    ssh_config_file: string to path for ssh config file, True to use default ssh config file
        or False to ignore default ssh config file
    ssh_known_hosts_file: string to path for ssh known hosts file, True to use default known
        file locations. Only applicable/needed if `auth_strict_key` is set to True
    on_init: callable that accepts the class instance as its only argument. this callable,
        if provided, is executed as the last step of object instantiation -- its purpose is
        primarily to provide a mechanism for scrapli community platforms to have an easy way
        to modify initialization arguments/object attributes without needing to create a
        class that extends the driver, instead allowing the community platforms to simply
        build from the GenericDriver or NetworkDriver classes, and pass this callable to do
        things such as appending to a username (looking at you RouterOS!!). Note that this
        is *always* a synchronous function (even for asyncio drivers)!
    on_open: callable that accepts the class instance as its only argument. this callable,
        if provided, is executed immediately after authentication is completed. Common use
        cases for this callable would be to disable paging or accept any kind of banner
        message that prompts a user upon connection
    on_close: callable that accepts the class instance as its only argument. this callable,
        if provided, is executed immediately prior to closing the underlying transport.
        Common use cases for this callable would be to save configurations prior to exiting,
        or to logout properly to free up vtys or similar
    transport: name of the transport plugin to use for the actual telnet/ssh/netconf
        connection. Available "core" transports are:
            - system
            - telnet
            - asynctelnet
            - ssh2
            - paramiko
            - asyncssh
        Please see relevant transport plugin section for details. Additionally third party
        transport plugins may be available.
    transport_options: dictionary of options to pass to selected transport class; see
        docs for given transport class for details of what to pass here
    channel_lock: True/False to lock the channel (threading.Lock/asyncio.Lock) during
        any channel operations, defaults to False
    channel_log: True/False or a string path to a file of where to write out channel logs --
        these are not "logs" in the normal logging module sense, but only the output that is
        read from the channel. In other words, the output of the channel log should look
        similar to what you would see as a human connecting to a device
    channel_log_mode: "write"|"append", all other values will raise ValueError,
        does what it sounds like it should by setting the channel log to the provided mode
    logging_uid: unique identifier (string) to associate to log messages; useful if you have
        multiple connections to the same device (i.e. one console, one ssh, or one to each
        supervisor module, etc.)

Returns:
    None

Raises:
    N/A
```

<details class="source">
    <summary>
        <span>Expand source code</span>
    </summary>
    <pre>
        <code class="python">
class NetconfBaseDriver(BaseDriver):
    host: str
    readable_datastores: List[str]
    writeable_datastores: List[str]
    strip_namespaces: bool
    strict_datastores: bool
    flatten_input: bool
    _netconf_base_channel_args: NetconfBaseChannelArgs

    @property
    def netconf_version(self) -> NetconfVersion:
        """
        Getter for 'netconf_version' attribute

        Args:
            N/A

        Returns:
            NetconfVersion: netconf_version enum

        Raises:
            N/A

        """
        return self._netconf_base_channel_args.netconf_version

    @netconf_version.setter
    def netconf_version(self, value: NetconfVersion) -> None:
        """
        Setter for 'netconf_version' attribute

        Args:
            value: NetconfVersion

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type NetconfVersion

        """
        if not isinstance(value, NetconfVersion):
            raise ScrapliTypeError

        self.logger.debug(f"setting 'netconf_version' value to '{value.value}'")

        self._netconf_base_channel_args.netconf_version = value

        if self._netconf_base_channel_args.netconf_version == NetconfVersion.VERSION_1_0:
            self._base_channel_args.comms_prompt_pattern = "]]>]]>"
        else:
            self._base_channel_args.comms_prompt_pattern = r"^##$"

    @property
    def client_capabilities(self) -> NetconfClientCapabilities:
        """
        Getter for 'client_capabilities' attribute

        Args:
            N/A

        Returns:
            NetconfClientCapabilities: netconf client capabilities enum

        Raises:
            N/A

        """
        return self._netconf_base_channel_args.client_capabilities

    @client_capabilities.setter
    def client_capabilities(self, value: NetconfClientCapabilities) -> None:
        """
        Setter for 'client_capabilities' attribute

        Args:
            value: NetconfClientCapabilities value for client_capabilities

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type NetconfClientCapabilities

        """
        if not isinstance(value, NetconfClientCapabilities):
            raise ScrapliTypeError

        self.logger.debug(f"setting 'client_capabilities' value to '{value.value}'")

        self._netconf_base_channel_args.client_capabilities = value

    @property
    def server_capabilities(self) -> List[str]:
        """
        Getter for 'server_capabilities' attribute

        Args:
            N/A

        Returns:
            list: list of strings of server capabilities

        Raises:
            N/A

        """
        return self._netconf_base_channel_args.server_capabilities or []

    @server_capabilities.setter
    def server_capabilities(self, value: NetconfClientCapabilities) -> None:
        """
        Setter for 'server_capabilities' attribute

        Args:
            value: list of strings of netconf server capabilities

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type list

        """
        if not isinstance(value, list):
            raise ScrapliTypeError

        self.logger.debug(f"setting 'server_capabilities' value to '{value}'")

        self._netconf_base_channel_args.server_capabilities = value

    @staticmethod
    def _determine_preferred_netconf_version(
        preferred_netconf_version: Optional[str],
    ) -> NetconfVersion:
        """
        Determine users preferred netconf version (if applicable)

        Args:
            preferred_netconf_version: optional string indicating users preferred netconf version

        Returns:
            NetconfVersion: users preferred netconf version

        Raises:
            ScrapliValueError: if preferred_netconf_version is not None or a valid option

        """
        if preferred_netconf_version is None:
            return NetconfVersion.UNKNOWN
        if preferred_netconf_version == "1.0":
            return NetconfVersion.VERSION_1_0
        if preferred_netconf_version == "1.1":
            return NetconfVersion.VERSION_1_1

        raise ScrapliValueError(
            "'preferred_netconf_version' provided with invalid value, must be one of: "
            "None, '1.0', or '1.1'"
        )

    @staticmethod
    def _determine_preferred_xml_parser(use_compressed_parser: bool) -> XmlParserVersion:
        """
        Determine users preferred xml payload parser

        Args:
            use_compressed_parser: bool indicating use of compressed parser or not

        Returns:
            XmlParserVersion: users xml parser version

        Raises:
            N/A

        """
        if use_compressed_parser is True:
            return XmlParserVersion.COMPRESSED_PARSER
        return XmlParserVersion.STANDARD_PARSER

    @property
    def xml_parser(self) -> etree.XMLParser:
        """
        Getter for 'xml_parser' attribute

        Args:
            N/A

        Returns:
            etree.XMLParser: parser to use for parsing xml documents

        Raises:
            N/A

        """
        if self._netconf_base_channel_args.xml_parser == XmlParserVersion.COMPRESSED_PARSER:
            return COMPRESSED_PARSER
        return STANDARD_PARSER

    @xml_parser.setter
    def xml_parser(self, value: XmlParserVersion) -> None:
        """
        Setter for 'xml_parser' attribute

        Args:
            value: enum indicating parser version to use

        Returns:
            None

        Raises:
            ScrapliTypeError: if value is not of type XmlParserVersion

        """
        if not isinstance(value, XmlParserVersion):
            raise ScrapliTypeError

        self._netconf_base_channel_args.xml_parser = value

    def _transport_factory(self) -> Tuple[Callable[..., Any], object]:
        """
        Determine proper transport class and necessary arguments to initialize that class

        Args:
            N/A

        Returns:
            Tuple[Callable[..., Any], object]: tuple of transport class and dataclass of transport
                class specific arguments

        Raises:
            N/A

        """
        transport_plugin_module = importlib.import_module(
            f"scrapli_netconf.transport.plugins.{self.transport_name}.transport"
        )

        transport_class = getattr(
            transport_plugin_module, f"Netconf{self.transport_name.capitalize()}Transport"
        )
        plugin_transport_args_class = getattr(transport_plugin_module, "PluginTransportArgs")

        _plugin_transport_args = {
            field.name: getattr(self, field.name) for field in fields(plugin_transport_args_class)
        }

        plugin_transport_args = plugin_transport_args_class(**_plugin_transport_args)

        return transport_class, plugin_transport_args

    def _build_readable_datastores(self) -> None:
        """
        Build a list of readable datastores based on server's advertised capabilities

        Args:
            N/A

        Returns:
            None

        Raises:
            N/A

        """
        self.readable_datastores = []
        self.readable_datastores.append("running")
        if "urn:ietf:params:netconf:capability:candidate:1.0" in self.server_capabilities:
            self.readable_datastores.append("candidate")
        if "urn:ietf:params:netconf:capability:startup:1.0" in self.server_capabilities:
            self.readable_datastores.append("startup")

    def _build_writeable_datastores(self) -> None:
        """
        Build a list of writeable/editable datastores based on server's advertised capabilities

        Args:
            N/A

        Returns:
            None

        Raises:
            N/A

        """
        self.writeable_datastores = []
        if "urn:ietf:params:netconf:capability:writeable-running:1.0" in self.server_capabilities:
            self.writeable_datastores.append("running")
        if "urn:ietf:params:netconf:capability:writable-running:1.0" in self.server_capabilities:
            # NOTE: iosxe shows "writable" (as of 2020.07.01) despite RFC being "writeable"
            self.writeable_datastores.append("running")
        if "urn:ietf:params:netconf:capability:candidate:1.0" in self.server_capabilities:
            self.writeable_datastores.append("candidate")
        if "urn:ietf:params:netconf:capability:startup:1.0" in self.server_capabilities:
            self.writeable_datastores.append("startup")

    def _validate_get_config_target(self, source: str) -> None:
        """
        Validate get-config source is acceptable

        Args:
            source: configuration source to get; typically one of running|startup|candidate

        Returns:
            None

        Raises:
            ScrapliValueError: if an invalid source was selected and strict_datastores is True

        """
        if source not in self.readable_datastores:
            msg = f"'source' should be one of {self.readable_datastores}, got '{source}'"
            self.logger.warning(msg)
            if self.strict_datastores is True:
                raise ScrapliValueError(msg)
            user_warning(title="Invalid datastore source!", message=msg)

    def _validate_edit_config_target(self, target: str) -> None:
        """
        Validate edit-config/lock/unlock target is acceptable

        Args:
            target: configuration source to edit/lock; typically one of running|startup|candidate

        Returns:
            None

        Raises:
            ScrapliValueError: if an invalid source was selected

        """
        if target not in self.writeable_datastores:
            msg = f"'target' should be one of {self.writeable_datastores}, got '{target}'"
            self.logger.warning(msg)
            if self.strict_datastores is True:
                raise ScrapliValueError(msg)
            user_warning(title="Invalid datastore target!", message=msg)

    def _validate_delete_config_target(self, target: str) -> None:
        """
        Validate delete-config/lock/unlock target is acceptable

        Args:
            target: configuration source to delete; typically one of startup|candidate

        Returns:
            None

        Raises:
            ScrapliValueError: if an invalid target was selected

        """
        if target == "running" or target not in self.writeable_datastores:
            msg = f"'target' should be one of {self.writeable_datastores}, got '{target}'"
            if target == "running":
                msg = "delete-config 'target' may not be 'running'"
            self.logger.warning(msg)
            if self.strict_datastores is True:
                raise ScrapliValueError(msg)
            user_warning(title="Invalid datastore target!", message=msg)

    def _build_base_elem(self) -> _Element:
        """
        Create base element for netconf operations

        Args:
            N/A

        Returns:
            _Element: lxml base element to use for netconf operation

        Raises:
            N/A

        """
        # pylint did not seem to want to be ok with assigning this as a class attribute... and its
        # only used here so... here we are
        self.message_id: int  # pylint: disable=W0201
        self.logger.debug(f"Building base element for message id {self.message_id}")
        base_xml_str = NetconfBaseOperations.RPC.value.format(message_id=self.message_id)
        self.message_id += 1
        base_elem = etree.fromstring(text=base_xml_str)
        return base_elem

    def _build_filter(self, filter_: str, filter_type: str = "subtree") -> _Element:
        """
        Create filter element for a given rpc

        The `filter_` string may contain multiple xml elements at its "root" (subtree filters); we
        will simply place the payload into a temporary "tmp" outer tag so that when we cast it to an
        etree object the elements are all preserved; without this outer "tmp" tag, lxml will scoop
        up only the first element provided as it appears to be the root of the document presumably.

        An example valid (to scrapli netconf at least) xml filter would be:

        ```
        <interface-configurations xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ifmgr-cfg">
            <interface-configuration>
                <active>act</active>
            </interface-configuration>
        </interface-configurations>
        <netconf-yang xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-man-netconf-cfg">
        </netconf-yang>
        ```

        Args:
            filter_: strings of filters to build into a filter element or (for subtree) a full
                filter string (in filter tags)
            filter_type: type of filter; subtree|xpath

        Returns:
            _Element: lxml filter element to use for netconf operation

        Raises:
            CapabilityNotSupported: if xpath selected and not supported on server
            ScrapliValueError: if filter_type is not one of subtree|xpath

        """
        if filter_type == "subtree":
            # tmp tags to place the users kinda not valid xml filter into
            _filter_ = f"<tmp>{filter_}</tmp>"
            # "validate" subtree filter by forcing it into xml, parser "flattens" it as well
            tmp_xml_filter_element = etree.fromstring(_filter_, parser=self.xml_parser)

            if tmp_xml_filter_element.getchildren()[0].tag == "filter":
                # if the user filter was already wrapped in filter tags we'll end up here, we will
                # blindly reuse the users filter but we'll make sure that the filter "type" is set
                xml_filter_elem = tmp_xml_filter_element.getchildren()[0]
                xml_filter_elem.attrib["type"] = "subtree"
            else:
                xml_filter_elem = etree.fromstring(
                    NetconfBaseOperations.FILTER_SUBTREE.value.format(filter_type=filter_type),
                )

                # iterate through the children inside the tmp tags and insert *those* elements into
                # the actual final filter payload
                for xml_filter_element in tmp_xml_filter_element:
                    # insert the subtree filter into the parent filter element
                    xml_filter_elem.insert(1, xml_filter_element)

        elif filter_type == "xpath":
            if "urn:ietf:params:netconf:capability:xpath:1.0" not in self.server_capabilities:
                msg = "xpath filter requested, but is not supported by the server"
                self.logger.exception(msg)
                raise CapabilityNotSupported(msg)
            xml_filter_elem = etree.fromstring(
                NetconfBaseOperations.FILTER_XPATH.value.format(
                    filter_type=filter_type, xpath=filter_
                ),
                parser=self.xml_parser,
            )
        else:
            raise ScrapliValueError(
                f"'filter_type' should be one of subtree|xpath, got '{filter_type}'"
            )
        return xml_filter_elem

    def _build_with_defaults(self, default_type: str = "report-all") -> _Element:
        """
        Create with-defaults element for a given operation

        Args:
            default_type: enumeration of with-defaults; report-all|trim|explicit|report-all-tagged

        Returns:
            _Element: lxml with-defaults element to use for netconf operation

        Raises:
            CapabilityNotSupported: if default_type provided but not supported by device
            ScrapliValueError: if default_type is not one of
                report-all|trim|explicit|report-all-tagged

        """

        if default_type in ["report-all", "trim", "explicit", "report-all-tagged"]:
            if (
                "urn:ietf:params:netconf:capability:with-defaults:1.0"
                not in self.server_capabilities
            ):
                msg = "with-defaults requested, but is not supported by the server"
                self.logger.exception(msg)
                raise CapabilityNotSupported(msg)
            xml_with_defaults_element = etree.fromstring(
                NetconfBaseOperations.WITH_DEFAULTS_SUBTREE.value.format(default_type=default_type),
                parser=self.xml_parser,
            )
        else:
            raise ScrapliValueError(
                "'default_type' should be one of report-all|trim|explicit|report-all-tagged, "
                f"got '{default_type}'"
            )
        return xml_with_defaults_element

    def _finalize_channel_input(self, xml_request: _Element) -> bytes:
        """
        Create finalized channel input (as bytes)

        Args:
            xml_request: finalized xml element to cast to bytes and add declaration to

        Returns:
            bytes: finalized bytes input -- with 1.0 delimiter or 1.1 encoding

        Raises:
            N/A

        """
        channel_input: bytes = etree.tostring(
            element_or_tree=xml_request, xml_declaration=True, encoding="utf-8"
        )

        if self.netconf_version == NetconfVersion.VERSION_1_0:
            channel_input = channel_input + b"]]>]]>"
        else:
            # format message for chunk (netconf 1.1) style message
            channel_input = b"#%b\n" % str(len(channel_input)).encode() + channel_input + b"\n##"

        return channel_input

    def _pre_get(self, filter_: str, filter_type: str = "subtree") -> NetconfResponse:
        """
        Handle pre "get" tasks for consistency between sync/async versions

        *NOTE*
        The channel input (filter_) is loaded up as an lxml etree element here, this is done with a
        parser that removes whitespace. This has a somewhat undesirable effect of making any
        "pretty" input not pretty, however... after we load the xml object (which we do to validate
        that it is valid xml) we dump that xml object back to a string to be used as the actual
        raw payload we send down the channel, which means we are sending "flattened" (not pretty/
        indented xml) to the device. This is important it seems! Some devices seme to not mind
        having the "nicely" formatted input (pretty xml). But! On devices that "echo" the inputs
        back -- sometimes the device will respond to our rpc without "finishing" echoing our inputs
        to the device, this breaks the core "read until input" processing that scrapli always does.
        For whatever reason if there are no line breaks this does not seem to happen? /shrug. Note
        that this comment applies to all of the "pre" methods that we parse a filter/payload!

        Args:
            filter_: string filter to apply to the get
            filter_type: type of filter; subtree|xpath

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(
            f"Building payload for 'get' operation. filter_type: {filter_type}, filter_: {filter_}"
        )

        # build base request and insert the get element
        xml_request = self._build_base_elem()
        xml_get_element = etree.fromstring(NetconfBaseOperations.GET.value)
        xml_request.insert(0, xml_get_element)

        # build filter element
        xml_filter_elem = self._build_filter(filter_=filter_, filter_type=filter_type)

        # insert filter element into parent get element
        get_element = xml_request.find("get")
        get_element.insert(0, xml_filter_elem)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(f"Built payload for 'get' operation. Payload: {channel_input.decode()}")
        return response

    def _pre_get_config(
        self,
        source: str = "running",
        filter_: Optional[str] = None,
        filter_type: str = "subtree",
        default_type: Optional[str] = None,
    ) -> NetconfResponse:
        """
        Handle pre "get_config" tasks for consistency between sync/async versions

        Args:
            source: configuration source to get; typically one of running|startup|candidate
            filter_: string of filter(s) to apply to configuration
            filter_type: type of filter; subtree|xpath
            default_type: string of with-default mode to apply when retrieving configuration

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(
            f"Building payload for 'get-config' operation. source: {source}, filter_type: "
            f"{filter_type}, filter: {filter_}, default_type: {default_type}"
        )
        self._validate_get_config_target(source=source)

        # build base request and insert the get-config element
        xml_request = self._build_base_elem()
        xml_get_config_element = etree.fromstring(
            NetconfBaseOperations.GET_CONFIG.value.format(source=source), parser=self.xml_parser
        )
        xml_request.insert(0, xml_get_config_element)

        if filter_ is not None:
            xml_filter_elem = self._build_filter(filter_=filter_, filter_type=filter_type)
            # insert filter element into parent get element
            get_element = xml_request.find("get-config")
            # insert *after* source, otherwise juniper seems to gripe, maybe/probably others as well
            get_element.insert(1, xml_filter_elem)

        if default_type is not None:
            xml_with_defaults_elem = self._build_with_defaults(default_type=default_type)
            get_element = xml_request.find("get-config")
            get_element.insert(2, xml_with_defaults_elem)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'get-config' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_edit_config(self, config: str, target: str = "running") -> NetconfResponse:
        """
        Handle pre "edit_config" tasks for consistency between sync/async versions

        Args:
            config: configuration to send to device
            target: configuration source to target; running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(
            f"Building payload for 'edit-config' operation. target: {target}, config: {config}"
        )
        self._validate_edit_config_target(target=target)

        xml_config = etree.fromstring(config, parser=self.xml_parser)

        # build base request and insert the edit-config element
        xml_request = self._build_base_elem()
        xml_edit_config_element = etree.fromstring(
            NetconfBaseOperations.EDIT_CONFIG.value.format(target=target)
        )
        xml_request.insert(0, xml_edit_config_element)

        # insert parent filter element to first position so that target stays first just for nice
        # output/readability
        edit_config_element = xml_request.find("edit-config")
        edit_config_element.insert(1, xml_config)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'edit-config' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_delete_config(self, target: str = "running") -> NetconfResponse:
        """
        Handle pre "edit_config" tasks for consistency between sync/async versions

        Args:
            target: configuration source to target; startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug(f"Building payload for 'delete-config' operation. target: {target}")
        self._validate_delete_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_validate_element = etree.fromstring(
            NetconfBaseOperations.DELETE_CONFIG.value.format(target=target), parser=self.xml_parser
        )
        xml_request.insert(0, xml_validate_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'delete-config' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_commit(self) -> NetconfResponse:
        """
        Handle pre "commit" tasks for consistency between sync/async versions

        Args:
            N/A

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'commit' operation")
        xml_request = self._build_base_elem()
        xml_commit_element = etree.fromstring(
            NetconfBaseOperations.COMMIT.value, parser=self.xml_parser
        )
        xml_request.insert(0, xml_commit_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'commit' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_discard(self) -> NetconfResponse:
        """
        Handle pre "discard" tasks for consistency between sync/async versions

        Args:
            N/A

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'discard' operation.")
        xml_request = self._build_base_elem()
        xml_commit_element = etree.fromstring(
            NetconfBaseOperations.DISCARD.value, parser=self.xml_parser
        )
        xml_request.insert(0, xml_commit_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'discard' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_lock(self, target: str) -> NetconfResponse:
        """
        Handle pre "lock" tasks for consistency between sync/async versions

        Args:
            target: configuration source to target; running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'lock' operation.")
        self._validate_edit_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_lock_element = etree.fromstring(
            NetconfBaseOperations.LOCK.value.format(target=target), parser=self.xml_parser
        )
        xml_request.insert(0, xml_lock_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(f"Built payload for 'lock' operation. Payload: {channel_input.decode()}")
        return response

    def _pre_unlock(self, target: str) -> NetconfResponse:
        """
        Handle pre "unlock" tasks for consistency between sync/async versions

        Args:
            target: configuration source to target; running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'unlock' operation.")
        self._validate_edit_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_lock_element = etree.fromstring(
            NetconfBaseOperations.UNLOCK.value.format(target=target, parser=self.xml_parser)
        )
        xml_request.insert(0, xml_lock_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'unlock' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_rpc(self, filter_: Union[str, _Element]) -> NetconfResponse:
        """
        Handle pre "rpc" tasks for consistency between sync/async versions

        Args:
            filter_: filter/rpc to execute

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'rpc' operation.")
        xml_request = self._build_base_elem()

        # build filter element
        if isinstance(filter_, str):
            xml_filter_elem = etree.fromstring(filter_, parser=self.xml_parser)
        else:
            xml_filter_elem = filter_

        # insert filter element
        xml_request.insert(0, xml_filter_elem)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(f"Built payload for 'rpc' operation. Payload: {channel_input.decode()}")
        return response

    def _pre_validate(self, source: str) -> NetconfResponse:
        """
        Handle pre "validate" tasks for consistency between sync/async versions

        Args:
            source: configuration source to validate; typically one of running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            CapabilityNotSupported: if 'validate' capability does not exist

        """
        self.logger.debug("Building payload for 'validate' operation.")

        if not any(
            cap in self.server_capabilities
            for cap in (
                "urn:ietf:params:netconf:capability:validate:1.0",
                "urn:ietf:params:netconf:capability:validate:1.1",
            )
        ):
            msg = "validate requested, but is not supported by the server"
            self.logger.exception(msg)
            raise CapabilityNotSupported(msg)

        self._validate_edit_config_target(target=source)

        xml_request = self._build_base_elem()
        xml_validate_element = etree.fromstring(
            NetconfBaseOperations.VALIDATE.value.format(source=source), parser=self.xml_parser
        )
        xml_request.insert(0, xml_validate_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'validate' operation. Payload: {channel_input.decode()}"
        )
        return response

    def _pre_copy_config(self, source: str, target: str) -> NetconfResponse:
        """
        Handle pre "copy_config" tasks for consistency between sync/async versions

        Note that source is not validated/checked since it could be a url or a full configuration
        element itself.

        Args:
            source: configuration, url, or datastore to copy into the target datastore
            target: copy config destination/target; typically one of running|startup|candidate

        Returns:
            NetconfResponse: scrapli_netconf NetconfResponse object containing all the necessary
                channel inputs (string and xml)

        Raises:
            N/A

        """
        self.logger.debug("Building payload for 'copy_config' operation.")

        self._validate_edit_config_target(target=target)

        xml_request = self._build_base_elem()
        xml_validate_element = etree.fromstring(
            NetconfBaseOperations.COPY_CONFIG.value.format(source=source, target=target),
            parser=self.xml_parser,
        )
        xml_request.insert(0, xml_validate_element)

        channel_input = self._finalize_channel_input(xml_request=xml_request)

        response = NetconfResponse(
            host=self.host,
            channel_input=channel_input.decode(),
            xml_input=xml_request,
            netconf_version=self.netconf_version,
            strip_namespaces=self.strip_namespaces,
        )
        self.logger.debug(
            f"Built payload for 'copy-config' operation. Payload: {channel_input.decode()}"
        )
        return response
        </code>
    </pre>
</details>


#### Ancestors (in MRO)
- scrapli.driver.base.base_driver.BaseDriver
#### Descendants
- scrapli_netconf.driver.async_driver.AsyncNetconfDriver
- scrapli_netconf.driver.sync_driver.NetconfDriver
#### Class variables

    
`flatten_input: bool`




    
`host: str`




    
`readable_datastores: List[str]`




    
`strict_datastores: bool`




    
`strip_namespaces: bool`




    
`writeable_datastores: List[str]`



#### Instance variables

    
`client_capabilities: scrapli_netconf.constants.NetconfClientCapabilities`

```text
Getter for 'client_capabilities' attribute

Args:
    N/A

Returns:
    NetconfClientCapabilities: netconf client capabilities enum

Raises:
    N/A
```



    
`netconf_version: scrapli_netconf.constants.NetconfVersion`

```text
Getter for 'netconf_version' attribute

Args:
    N/A

Returns:
    NetconfVersion: netconf_version enum

Raises:
    N/A
```



    
`server_capabilities: List[str]`

```text
Getter for 'server_capabilities' attribute

Args:
    N/A

Returns:
    list: list of strings of server capabilities

Raises:
    N/A
```



    
`xml_parser: lxml.etree.XMLParser`

```text
Getter for 'xml_parser' attribute

Args:
    N/A

Returns:
    etree.XMLParser: parser to use for parsing xml documents

Raises:
    N/A
```





### NetconfBaseOperations


```text
An enumeration.
```

<details class="source">
    <summary>
        <span>Expand source code</span>
    </summary>
    <pre>
        <code class="python">
class NetconfBaseOperations(Enum):
    FILTER_SUBTREE = "<filter type='{filter_type}'></filter>"
    FILTER_XPATH = "<filter type='{filter_type}' select='{xpath}'></filter>"
    WITH_DEFAULTS_SUBTREE = (
        "<with-defaults xmlns='urn:ietf:params:xml:ns:yang:ietf-netconf-with-defaults'>"
        "{default_type}</with-defaults>"
    )
    GET = "<get></get>"
    GET_CONFIG = "<get-config><source><{source}/></source></get-config>"
    EDIT_CONFIG = "<edit-config><target><{target}/></target></edit-config>"
    DELETE_CONFIG = "<delete-config><target><{target}/></target></delete-config>"
    COPY_CONFIG = (
        "<copy-config><target><{target}/></target><source><{source}/></source></copy-config>"
    )
    COMMIT = "<commit/>"
    DISCARD = "<discard-changes/>"
    LOCK = "<lock><target><{target}/></target></lock>"
    UNLOCK = "<unlock><target><{target}/></target></unlock>"
    RPC = "<rpc xmlns='urn:ietf:params:xml:ns:netconf:base:1.0' message-id='{message_id}'></rpc>"
    VALIDATE = "<validate><source><{source}/></source></validate>"
        </code>
    </pre>
</details>


#### Ancestors (in MRO)
- enum.Enum
#### Class variables

    
`COMMIT`




    
`COPY_CONFIG`




    
`DELETE_CONFIG`




    
`DISCARD`




    
`EDIT_CONFIG`




    
`FILTER_SUBTREE`




    
`FILTER_XPATH`




    
`GET`




    
`GET_CONFIG`




    
`LOCK`




    
`RPC`




    
`UNLOCK`




    
`VALIDATE`




    
`WITH_DEFAULTS_SUBTREE`