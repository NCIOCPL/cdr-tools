#!/usr/bin/env python3

"""Convert Drupal JSON values to CDR XML.

This is a temporary script to be replaced by nodes2xml.py when the
core Drupal JSON:API module has been enabled for the cancer.gov CMS.

This script takes as input the JSON files found in the current
working directory and converts them into XML files suitable for
import into the CDR as new Summary documents. The JSON files will
have been created directly on the Drupal server using an edited
copy of the fetch-svpc-json.php script found in this directory.
See the comments at the top of that script for additional details.

No, this isn't very pretty code. It's intended to be discarded
before too much longer. :-)
"""

from json import load
from pathlib import Path
from re import match
from time import sleep
from lxml import etree, html
from lxml.builder import E
from requests import get

INLINE = dict(em="Emphasis", strong="Strong")
NS = "{cips.nci.nih.gov/cdr}"
IGNORE = "div", "drupal-entity", "button"
CANCER_GOV = "https://www.cancer.gov"

def check_url(url):
    if not match(r"^http.*/node/\d+.*$", url):
        return url
    response = get(url)
    sleep(.5)
    if response.ok:
        return response.url
    print(url, response.reason)
    return url

def get_text(node):
    if node is None:
        return ""
    return "".join(node.itertext("*"))

def map_node(tag, node, attributes=None):
    if tag in ("ExternalRef", "GlossaryTermRef"):
        etree.strip_tags(node, "em")
    children = []
    if node.text:
        children = [node.text]
    for child in node:
        if child.tag in INLINE:
            mapped_tag = INLINE[child.tag]
            children.append(map_node(mapped_tag, child))
        elif child.tag == "a":
            text = get_text(child)
            cdr_id = child.get("data-glossary-id")
            if cdr_id:
                attrs = {NS + "href": cdr_id}
                children.append(map_node("GlossaryTermRef", child, attrs))
            elif child.get("data-entity-type") == "node":
                url = check_url(CANCER_GOV + child.get("href"))
                attrs = {NS + "xref": url}
                children.append(map_node("ExternalRef", child, attrs))
            else:
                attrs = {NS + "xref": child.get("href")}
                children.append(map_node("ExternalRef", child, attrs))
        elif child.tag == "br":
            children.append("\n")
        elif child.tag == "ul":
            children.append(parse_list(child))
        elif child.tag == "span":
            children.append(get_text(child))
        elif child.tag not in IGNORE:
            raise Exception(f"{node.tag} has unexpected {child.tag}")
        if child.tail:
            children.append(child.tail)
    element = E(tag, *children)
    if attributes:
        for key in attributes:
            element.set(key, attributes[key])
    return element

def parse_list(node):
    items = []
    for item in node:
        if item.tag != "li":
            raise Exception(f"ul has unexpected {item.tag}")
        items.append(map_node("ListItem", item))
    return E("ItemizedList", *items, Style="bullet")

def parse_block(heading, content, section_type=None):
    elements = html.fragments_fromstring(content.strip())
    sections = []
    children = []
    grandchildren = []
    greatgrandchildren = []
    subsection = subsubsection = False
    if heading:
        children.append(E("Title", heading))
    if section_type:
        children.append(E("SectMetaData", E("SectionType", section_type)))
    for element in elements:
        if element.tag == "p":
            if not element.getchildren():
                if element.text is None or not element.text.strip():
                    if element.tail is None or not element.tail.strip():
                        continue
            if subsubsection:
                greatgrandchildren.append(map_node("Para", element))
            elif subsection:
                grandchildren.append(map_node("Para", element))
            else:
                children.append(map_node("Para", element))
        elif element.tag == "ul":
            if subsubsection:
                greatgrandchildren.append(parse_list(element))
            elif subsection:
                grandchildren.append(parse_list(element))
            else:
                children.append(parse_list(element))
        elif element.tag == "h2":
            if greatgrandchildren:
                grandchildren.append(E("SummarySection", *greatgrandchildren))
                greatgrandchildren = []
                subsubsection = False
            if grandchildren:
                children.append(E("SummarySection", *grandchildren))
                grandchildren = []
                subsection = False
            if children:
                sections.append(E("SummarySection", *children))
            children = [map_node("Title", element)]
        elif element.tag == "h3":
            if greatgrandchildren:
                grandchildren.append(E("SummarySection", *greatgrandchildren))
                greatgrandchildren = []
                subsubsection = False
            if grandchildren:
                children.append(E("SummarySection", *grandchildren))
            grandchildren = [map_node("Title", element)]
            subsection = True
        elif element.tag == "h4":
            if greatgrandchildren:
                grandchildren.append(E("SummarySection", *greatgrandchildren))
            greatgrandchildren = [map_node("Title", element)]
            subsubsection = True
        elif element.tag not in IGNORE:
            raise Exception(f"found top-level {element.tag}")
    if greatgrandchildren:
        grandchildren.append(E("SummarySection", *greatgrandchildren))
    if grandchildren:
        children.append(E("SummarySection", *grandchildren))
    if children:
        sections.append(E("SummarySection", *children))
    return sections


NSMAP = dict(cdr="cips.nci.nih.gov/cdr")
english_titles = {}
for p in Path(".").glob("node-*-en.json"):
    with p.open(encoding="utf-8") as fp:
        values = load(fp)
        nid = values["nid"][0]["value"]
        title = values["title"][0]["value"].strip()
        english_titles[nid] = title
for p in Path(".").glob("node-*-e*.json"):
    with p.open(encoding="utf-8") as fp:
        values = load(fp)
    nid = values["nid"][0]["value"]
    langcode = values["langcode"][0]["value"]
    print(f"{nid} ({langcode})")
    body_field = "field_article_body"
    heading_field = "field_body_section_heading"
    content_field = "field_body_section_content"
    node_type = values["type"][0]["target_id"]
    if node_type == "cgov_mini_landing":
        body_field = "field_landing_contents"
        heading_field = "field_content_heading"
        content_field = "field_html_content"
    title = values["title"][0]["value"].strip()
    cthp_title = None
    if values["field_card_title"]:
        cthp_title = values["field_card_title"][0]["value"].strip()
    browser_title = values["field_browser_title"][0]["value"].strip()
    language = "Spanish" if langcode == "es" else "English"
    alias = values["path"][0]["alias"].strip()
    summary_type = alias.split("/")[-1].split("-")[-1]
    if langcode == "es":
        url = f"https://www.cancer.gov/espanol{alias}"
    else:
        url = f"https://www.cancer.gov{alias}"
    description = values["field_page_description"][0]["value"].strip()
    #date_last_modified = values["field_date_posted"][0]["value"]
    date_last_modified = None
    if values.get("field_date_updated"):
        date_last_modified = values["field_date_updated"][0].get("value")
    intro = None
    if values.get("field_intro_text"):
        intro = values["field_intro_text"][0]["value"]
    keywords = "" # values["field_hhs_syndication"][0]["keywords"]
    root = etree.Element("Summary", SVPC="Yes", nsmap=NSMAP)
    root.set("ModuleOnly", "Yes")
    root.set("AvailableAsModule", "Yes")
    ctl = etree.SubElement(root, "CdrDocCtl")
    instructions = "{ The document ID will be assigned automatically }"
    pi = etree.ProcessingInstruction("xm-replace_text", instructions)
    ctl.append(E("DocId", pi))
    ctl.append(E("DocTitle", title))
    meta = etree.SubElement(root, "SummaryMetaData")
    etree.SubElement(meta, "SummaryType").text = summary_type
    etree.SubElement(meta, "SummaryAudience").text = "Patients"
    etree.SubElement(meta, "SummaryLanguage").text = language
    etree.SubElement(meta, "SummaryDescription").text = description
    child = etree.SubElement(meta, "SummaryURL")
    child.text = title
    child.set(NS + "xref", url)
    topic = etree.SubElement(meta, "MainTopics")
    etree.SubElement(topic, "Term")
    child = etree.SubElement(meta, "SummaryKeyWords")
    etree.SubElement(child, "SummaryKeyWord").text = keywords
    etree.SubElement(root, "SummaryTitle").text = title
    child = etree.SubElement(root, "AltTitle", TitleType="Browser")
    child.text = browser_title
    if cthp_title:
        attrs = dict(TitleType="CancerTypeHomePage")
        child = etree.SubElement(root, "AltTitle", **attrs)
        child.text = cthp_title
    #section = etree.SubElement(root, "SummarySection")
    #section_meta = etree.SubElement(section, "SectMetaData")
    #etree.SubElement(section_meta, "SectionType").text = "Introductory Text"
    #etree.SubElement(section, "Para").text = intro
    if intro:
        for section in parse_block("", intro, "Introductory Text"):
            root.append(section)
    for section in values[body_field]:
        target_id = section["target_id"]
        path = f"section-{target_id}-{langcode}.json"
        # print(path)
        with open(path, encoding="utf-8") as fp:
            values = load(fp)
        heading = None
        section_heading = values.get(heading_field)
        if section_heading:
            node = html.fromstring(section_heading[0]["value"].strip())
            heading = get_text(node).strip()
        content = values.get(content_field, [])
        for block in content:
            for section in parse_block(heading, block["value"]):
                root.append(section)
            heading = None
    if language == "Spanish":
        english_title = english_titles.get(nid)
        if english_title:
            etree.SubElement(root, "TranslationOf").text = english_title
    if date_last_modified:
        etree.SubElement(root, "DateLastModified").text = date_last_modified
    with open(f"{nid}-{langcode}.xml", "w", encoding="utf-8") as fp:
        fp.write('<?xml version="1.0"?>\n')
        fp.write('<!DOCTYPE Summary SYSTEM "Summary.dtd">\n')
        fp.write(etree.tostring(root, pretty_print=True, encoding="Unicode"))
