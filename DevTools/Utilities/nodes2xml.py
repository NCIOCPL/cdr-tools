#!/usr/bin/env python

"""Transform Drupal SVPC nodes into CDR XML documents.

usage: ./nodes2xml.py node-id [node-id ...]
"""

from argparse import ArgumentParser
from datetime import datetime
from functools import cached_property
from json import dump, load
from re import match as re_match
from time import sleep
from zipfile import ZipFile
from lxml import etree, html
from lxml.builder import E
from requests import get
from cdr import Logging


class Control:

    URL = "https://www-cms.cancer.gov"
    LANGCODES = "en", "es"
    NODE_TYPES = dict(
        cgov_article="field_article_body",
        cgov_mini_landing="field_landing_contents",
    )

    def run(self):
        """Top-level entry point for this script."""

        start = datetime.now()
        for nid in self.nids:
            opts = {}
            for langcode in self.LANGCODES:
                values = self.fetch(nid, langcode)
                if values:
                    if self.save:
                        path = f"{nid}-{langcode}.json"
                        with open(path, "w", encoding="utf-8") as fp:
                            dump(values, fp, indent=2)
                    summary = Summary(self, values, **opts)
                    summary.write(self.zipfile)
                    self.logger.info("added %s", summary.filename)
                    opts["english_summary"] = summary
        self.logger.info("summaries saved in %s", self.zipfile.filename)
        self.zipfile.close()
        self.logger.info("elapsed: %s", datetime.now() - start)

    def fetch(self, nid, langcode):
        """Get the values for a node's translation.

        Required positional arguments:
          nid - integer node ID
          langcode - "en" or "es"

        Return:
          dictionary of values
        """

        if self.directory:
            path = f"{self.directory}/{nid}-{langcode}.json"
            with open(path, encoding="utf-8") as fp:
                return load(fp)
        prefix = "espanol/" if langcode == "es" else ""
        for node_type, include in self.NODE_TYPES.items():
            parms = f"filter[drupal_internal__nid]={nid}&include={include}"
            url = f"{self.url}/{prefix}jsonapi/node/{node_type}?{parms}"
            response = get(url, timeout=60)
            if response.ok:
                return response.json()
        raise RuntimeError(f"{nid} ({langcode}): {response.reason}")

    @cached_property
    def directory(self):
        """Optional location of cached json."""
        return self.opts.directory

    @cached_property
    def logger(self):
        """How we record what we do."""
        return Logging.get_logger("nodes2xml", console=True)

    @cached_property
    def nids(self):
        """IDs of nodes to fetch and transform to XML."""
        return self.opts.nids

    @cached_property
    def opts(self):
        """Runtime options from the command-line."""

        parser = ArgumentParser()
        parser.add_argument("--url", "-u", default=self.URL)
        parser.add_argument("nids", type=int, nargs="+")
        parser.add_argument("--directory", "-d")
        parser.add_argument("--save", "-s", action="store_true")
        return parser.parse_args()

    @cached_property
    def save(self):
        """If True, save a copy of the JSON from Drupal."""

    @cached_property
    def url(self):
        """Base URL for fetching node JSON."""
        return self.opts.url

    @cached_property
    def url_cache(self):
        """Cache of URL mappings."""
        return {}

    @cached_property
    def zipfile(self):
        """Compressed archive in which we save the serialized XML documents."""

        now = datetime.now()
        stamp = now.strftime("%Y%m%d%H%M%S")
        filename = f"svpc-summaries-{stamp}.zip"
        return ZipFile(filename, "w")


class Summary:
    """Summary document built from Drupal article values."""

    CANCER_GOV = "https://www.cancer.gov"
    IGNORE = "div", "drupal-entity", "button"
    INLINE = dict(em="Emphasis", strong="Strong")
    NS = "{cips.nci.nih.gov/cdr}"
    NSMAP = {"cdr": "cips.nci.nih.gov/cdr"}

    def __init__(self, control, values, **opts):
        """Capture the caller's values.

        Required positional arguments:
          control - access to the URL cache and logging
          values - dictionary of values fetched from Druapl's jsonapi

        Optional keyword argument:
          english_summary - for access to the original summary title
        """

        self.__control = control
        self.__values = values
        self.__opts = opts

    def write(self, zipfile):
        """Save the serialized summary XML to the compressed archive.

        Required positional argument:
          zipfile - ZipFile object to which we add the summary's XML
        """

        document = "\n".join([
            '<?xml version="1.0"?>',
            '<!DOCTYPE Summary SYSTEM "Summary.dtd">',
            etree.tostring(self.root, pretty_print=True, encoding="Unicode"),
        ])
        zipfile.writestr(self.filename, document)

    @cached_property
    def alias(self):
        """URL alias for the summary."""
        return self.attributes["path"]["alias"].strip()

    @cached_property
    def attributes(self):
        """Values contained directly in the node."""
        return self.data["attributes"]

    @cached_property
    def browser_title(self):
        """String to be used for the web page's head/title element."""
        return self.attributes["field_browser_title"].strip()

    @cached_property
    def cdr_doc_ctl(self):
        """Top block added for XMetaL only."""

        block = etree.Element("CdrDocCtl")
        instructions = "{ The document ID will be assigned automatically }"
        pi = etree.ProcessingInstruction("xm-replace_text", instructions)
        block.append(E("DocId", pi))
        block.append(E("DocTitle", self.title))
        return block

    @cached_property
    def content_field(self):
        """Name of section content field, depending on node type."""

        if self.node_type == "cgov_mini_landing":
            return "field_html_content"
        return "field_body_section_content"

    @cached_property
    def cthp_title(self):
        """Title for the cancer-type home page card."""
        return self.attributes.get("field_card_title", "").strip() or None

    @cached_property
    def data(self):
        """Wrapper for values directly contained in the node."""
        return self.__values["data"][0]

    @cached_property
    def date_last_modified(self):
        """When the summary was last modified, if available."""
        return self.attributes.get("field_date_updated")

    @cached_property
    def description(self):
        """Brief description for the summary."""
        return self.attributes["field_page_description"].strip()

    @cached_property
    def english_summary(self):
        """Summary of which this summary is a translation, if appropriate."""
        return self.__opts.get("english_summary")

    @cached_property
    def filename(self):
        """Name under which the serialized XML will be stored."""
        return f"{self.nid}-{self.langcode}.xml"

    @cached_property
    def heading_field(self):
        """Name of section heading field, depending on node type."""

        if self.node_type == "cgov_mini_landing":
            return "field_content_heading"
        return "field_body_section_heading"

    @cached_property
    def included(self):
        """This is where the summary section data is captured."""
        return self.__values["included"]

    @cached_property
    def intro(self):
        """Introductory text for the summary."""

        intro_text = self.attributes.get("field_intro_text", {})
        return intro_text.get("value") or None

    @cached_property
    def keywords(self):
        """So far, this is always an empty string, but who knows?"""
        return self.attributes["field_hhs_syndication"]["keywords"].strip()

    @cached_property
    def langcode(self):
        """Either "en" or "es"."""
        return self.attributes["langcode"]

    @cached_property
    def language(self):
        """English or Spanish."""
        return "Spanish" if self.langcode == "es" else "English"

    @cached_property
    def nid(self):
        """Unique ID for the summary's Drupal node."""
        return self.attributes["drupal_internal__nid"]

    @cached_property
    def node_type(self):
        """Either cgov_article or cgov_mini_landing"""
        return self.data["type"].split("--")[-1]

    @cached_property
    def root(self):
        """Top-level element of XML document for summary."""

        root = etree.Element("Summary", SVPC="Yes", nsmap=self.NSMAP)
        root.set("ModuleOnly", "Yes")
        root.set("AvailableAsModule", "Yes")
        root.append(self.cdr_doc_ctl)
        root.append(self.summary_meta_data)
        etree.SubElement(root, "SummaryTitle").text = self.title
        child = etree.SubElement(root, "AltTitle", TitleType="Browser")
        child.text = self.browser_title
        if self.cthp_title:
            attrs = dict(TitleType="CancerTypeHomePage")
            child = etree.SubElement(root, "AltTitle", **attrs)
            child.text = self.cthp_title
        if self.intro:
            opts = dict(section_type="Introductory Text")
            for section in self.parse_block(self.intro, **opts):
                root.append(section)
        for section in self.sections:
            root.append(section)
        if self.english_summary:
            english_title = self.english_summary.title
            etree.SubElement(root, "TranslationOf").text = english_title
        if self.date_last_modified:
            last_mod = self.date_last_modified
            etree.SubElement(root, "DateLastModified").text = last_mod
        return root

    @cached_property
    def sections(self):
        """Top-level summary section DOM elements."""

        sections = []
        for item in self.included:
            heading = None
            attributes = item.get("attributes", {})
            heading_field = attributes.get(self.heading_field)
            if heading_field:
                node = html.fromstring(heading_field["value"].strip())
                heading = self.get_text(node).strip()
            content = attributes.get(self.content_field, {}).get("value")
            if content:
                for section in self.parse_block(content, heading=heading):
                    sections.append(section)
        return sections

    @cached_property
    def summary_meta_data(self):
        """Block for the information about the summary."""

        block = etree.Element("SummaryMetaData")
        etree.SubElement(block, "SummaryType").text = self.summary_type
        etree.SubElement(block, "SummaryAudience").text = "Patients"
        etree.SubElement(block, "SummaryLanguage").text = self.language
        etree.SubElement(block, "SummaryDescription").text = self.description
        child = etree.SubElement(block, "SummaryURL")
        child.text = self.title
        child.set(self.NS + "xref", self.url)
        child = etree.SubElement(block, "MainTopics")
        etree.SubElement(child, "Term")
        child = etree.SubElement(block, "SummaryKeyWords")
        etree.SubElement(child, "SummaryKeyWord").text = self.keywords
        return block

    @cached_property
    def summary_type(self):
        """Last part of the summary's URL alias."""
        return self.alias.split("/")[-1].split("-")[-1]

    @cached_property
    def title(self):
        """String for the title of the summary."""
        return self.attributes.get("title", "").strip()

    @cached_property
    def url(self):
        """Web address for the summary."""

        if self.langcode == "es":
            return f"https://www.cancer.gov/espanol{self.alias}"
        return f"https://www.cancer.gov{self.alias}"

    def check_url(self, url):
        """Map URL to a redirected substitute URL if appropriate.

        Required positional argument:
          url = original URL

        Return:
          redirect URL or original URL if not redirected
        """

        if not re_match(r"^http.*/node/\d+.*$", url):
            return url
        if url in self.__control.url_cache:
            return self.__control.url_cache[url]
        response = get(url, timeout=60)
        sleep(.5)
        if response.ok:
            self.__control.url_cache[url] = response.url
            return response.url
        self.__control.logger.error("%s: %s", url, response.reason)
        self.__control.url_cache[url] = url
        return url

    @staticmethod
    def get_text(node):
        """Extract text content from DOM node.

        Required positional argument:
          node - DOM node from which to extract text content

        Return:
          possibly empty string
        """

        if node is None:
            return ""
        return "".join(node.itertext("*"))

    def map_node(self, tag, node, **kwargs):
        """Create DOM node suitable for use in CDR Summary document.

        Required positional arguments:
          tag - name of DOM element to be created
          node - DOM node parsed from serialized HTML

        Optional keyword argument
          attributes - dictionary of attributes to be applied to new node

        Return:
          DOM node expected by CDR XML schema for Summary documents
        """

        if tag in ("ExternalRef", "GlossaryTermRef"):
            etree.strip_tags(node, "em")
        children = []
        if node.text:
            children = [node.text]
        for child in node:
            if child.tag in self.INLINE:
                mapped_tag = self.INLINE[child.tag]
                children.append(self.map_node(mapped_tag, child))
            elif child.tag == "a":
                text = self.get_text(child)
                cdr_id = child.get("data-glossary-id")
                new_tag = "ExternalRef"
                if cdr_id:
                    opts = dict(attributes={f"{self.NS}href": cdr_id})
                    new_tag = "GlossaryTermRef"
                elif child.get("data-entity-type") == "node":
                    url = self.check_url(self.CANCER_GOV + child.get("href"))
                    opts = dict(attributes={f"{self.NS}xref": url})
                else:
                    url = child.get("href")
                    opts = dict(attributes={f"{self.NS}xref": url})
                children.append(self.map_node(new_tag, child, **opts))
            elif child.tag == "br":
                children.append("\n")
            elif child.tag == "ul":
                children.append(self.parse_list(child))
            elif child.tag == "span":
                children.append(self.get_text(child))
            elif child.tag not in self.IGNORE:
                raise RuntimeError(f"{node.tag} has unexpected {child.tag}")
            if child.tail:
                children.append(child.tail)
        element = E(tag, *children)
        attributes = kwargs.get("attributes")
        if attributes:
            for key in attributes:
                element.set(key, attributes[key])
        return element

    def parse_block(self, html_string, **kwargs):
        """Convert serialized HTML into DOM elements.

        Required positional argument:
          html_string - serialized HTML

        Optional keyword arguments:
          heading - string for block title
          section_type - text content for SectionType element

        Return:
          sequence of (possibly nested) DOM SummarySection elements
        """

        sections = []
        children = []
        grandchildren = []
        greatgrandchildren = []
        subsection = subsubsection = False
        heading = kwargs.get("heading")
        section_type = kwargs.get("section_type")
        if heading:
            children.append(E("Title", heading))
        if section_type:
            children.append(E("SectMetaData", E("SectionType", section_type)))
        for element in html.fragments_fromstring(html_string.strip()):
            if element.tag == "p":
                if not element.getchildren():
                    if element.text is None or not element.text.strip():
                        if element.tail is None or not element.tail.strip():
                            continue
                if subsubsection:
                    greatgrandchildren.append(self.map_node("Para", element))
                elif subsection:
                    grandchildren.append(self.map_node("Para", element))
                else:
                    children.append(self.map_node("Para", element))
            elif element.tag == "ul":
                if subsubsection:
                    greatgrandchildren.append(self.parse_list(element))
                elif subsection:
                    grandchildren.append(self.parse_list(element))
                else:
                    children.append(self.parse_list(element))
            elif element.tag == "h2":
                if greatgrandchildren:
                    summary_section = E("SummarySection", *greatgrandchildren)
                    grandchildren.append(summary_section)
                    greatgrandchildren = []
                    subsubsection = False
                if grandchildren:
                    children.append(E("SummarySection", *grandchildren))
                    grandchildren = []
                    subsection = False
                if children:
                    sections.append(E("SummarySection", *children))
                children = [self.map_node("Title", element)]
            elif element.tag == "h3":
                if greatgrandchildren:
                    summary_section = E("SummarySection", *greatgrandchildren)
                    grandchildren.append(summary_section)
                    greatgrandchildren = []
                    subsubsection = False
                if grandchildren:
                    children.append(E("SummarySection", *grandchildren))
                grandchildren = [self.map_node("Title", element)]
                subsection = True
            elif element.tag == "h4":
                if greatgrandchildren:
                    summary_section = E("SummarySection", *greatgrandchildren)
                    grandchildren.append(summary_section)
                greatgrandchildren = [self.map_node("Title", element)]
                subsubsection = True
            elif element.tag not in self.IGNORE:
                raise Exception(f"found top-level {element.tag}")
        if greatgrandchildren:
            grandchildren.append(E("SummarySection", *greatgrandchildren))
        if grandchildren:
            children.append(E("SummarySection", *grandchildren))
        if children:
            sections.append(E("SummarySection", *children))
        return sections

    def parse_list(self, node):
        """Parse the members of a list (li) node.

        Required positional argument:
          node - DOM li node

        Return:
          ItemizedList element
        """

        items = []
        for item in node:
            if item.tag != "li":
                raise Exception(f"ul has unexpected {item.tag}")
            items.append(self.map_node("ListItem", item))
        return E("ItemizedList", *items, Style="bullet")


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
