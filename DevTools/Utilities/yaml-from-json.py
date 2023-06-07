#!/usr/bin/env python3

"""Generate YAML sample content for the Drupal CMS.

Takes values serialized as JSON from stdin and writes YAML to stdout.

There is one command-line argument (--type) which is required: cis or dis,
indicating the type of the Drupal node (pdq_cancer_information_summary or
pdq_drug_information_summary).

We're creating the YAML serialization by hand because the software
which consumes it only understands a subset of valid YAML syntax. :-(
"""

from argparse import ArgumentParser
from collections import namedtuple
from datetime import date
from json import load
from re import sub
from sys import stdin


class Summary:
    """Values for a PDQ Summary with YAML serialization."""

    TODAY = date.today()
    CIS_HTML_INDENT = "  " * 6
    DIS_BODY_INDENT = "  " * 4
    PREFIX = "https://www.cancer.gov"
    TYPES = "cis", "dis"

    def __init__(self, values, content_type):
        """Remember the caller's values.

        Pass:
            values - dictionary of values parsed from JSON input
            content_type - "cis" or "dis"
        """
        self.values = values
        self.type = content_type

    @property
    def yaml(self):
        """YAML serialization of node's values."""

        if not hasattr(self, "_yaml"):
            if self.type == "cis":
                self._yaml = self.__create_cis_yaml()
            else:
                self._yaml = self.__create_dis_yaml()
        return self._yaml

    def __create_cis_yaml(self):
        """Create YAML serialization for a Cancer Information Summary node."""

        keywords = self.values.get("keywords", "")
        en = self.values["en"]
        values = namedtuple("Values", en.keys())(*en.values())
        lines = [
            "- entity: node",
            "  type: pdq_cancer_information_summary",
        ] + self.__add_cis_fields(values, keywords=keywords)
        es = self.values.get("es")
        if es:
            values = namedtuple("Values", es.keys())(*es.values())
            lines += self.__add_cis_fields(values, "__ES")
        return "\n".join(lines)

    def __create_dis_yaml(self):
        """Create YAML serialization for a Drug Information Summary node."""

        values = self.values
        values = namedtuple("Values", values.keys())(*values.values())
        lines = [
            "- entity: node",
            "  type: pdq_drug_information_summary",
            "  status: 1",
            "  langcode: en",
            "  title: {}".format(self.__quote(values.title)),
            "  moderation_state:",
            "    value: published",
            "  field_pdq_url:",
            "    value: {}".format(values.url),
            "  field_pdq_cdr_id:",
            "    value: {}".format(values.cdr_id),
            "  field_date_posted:",
            "    value: '{}'".format(values.posted_date or self.TODAY),
            "  field_date_updated:",
            "    value: '{}'".format(values.updated_date or self.TODAY),
            "  field_page_description:",
            "    value: {}".format(self.__quote(values.description)),
            "  field_public_use:",
            "    value: 0",
        ]
        if values.audio_id:
            lines += [
                "  field_pdq_audio_id:",
                "    value: {}".format(values.audio_id),
            ]
        if values.pron:
            lines += [
                "  field_pdq_pronunciation_key:",
                "    value: {}".format(values.pron),
            ]
        lines += [
            "  body:",
            "    - format: raw_html",
            "      value: |",
        ] + self.__indent(values.body, self.DIS_BODY_INDENT)
        return "\n".join(lines)

    def __add_cis_fields(self, values, suffix="", keywords=None):
        """Serialize the values for one of the summary's languages.

        Pass:
          values - dictionary of field values
          suffix - optional suffix identifying the Spanish values
          keywords - optional string for syndication keywords

        Return:
          string containing YAML serialization of field values
        """

        # Spanish and English fields use different syntax (don't ask).
        if suffix:
            lines = [
                f"  title{suffix}:",
                f"    value: {self.__quote(values.title)}",
                f"  status{suffix}:",
                "    value: 1",
                f"  langcode{suffix}:",
                "    value: es",
            ]
        else:
            keywords = keywords or "''"
            lines = [
                f"  title: {self.__quote(values.title)}",
                "  status: 1",
                "  langcode: en",
                "  field_hhs_syndication:",
                "    - syndicate: 1",
                f"      keywords: {keywords}",
            ]
        svpc = getattr(values, "svpc", "0")
        suppress_otp = getattr(values, "suppress_otp", "0")
        intro_text = (getattr(values, "intro_text", "") or "").strip()
        intro_text_lines = [line.strip() for line in intro_text.splitlines()]
        intro_text = ["      " + line for line in intro_text_lines if line]
        lines += [
            f"  moderation_state{suffix}:",
            "    value: published",
            f"  field_pdq_url{suffix}:",
            f"    value: {values.url.replace(self.PREFIX, '')}",
            f"  field_pdq_cdr_id{suffix}:",
            f"    value: {values.cdr_id}",
            f"  field_pdq_audience{suffix}:",
            f"    value: {values.audience.replace(' pro', ' Pro')}",
            f"  field_pdq_summary_type{suffix}:",
            f"    value: {values.summary_type}",
            f"  field_date_posted{suffix}:",
            f"    value: '{values.posted_date or self.TODAY}'",
            f"  field_date_updated{suffix}:",
            f"    value: '{values.updated_date or self.TODAY}'",
            f"  field_browser_title{suffix}:",
            f"    value: {self.__quote(values.browser_title)}",
            f"  field_cthp_card_title{suffix}:",
            f"    value: {self.__quote(values.cthp_card_title)}",
            f"  field_page_description{suffix}:",
            f"    value: {self.__quote(values.description)}",
            f"  field_public_use{suffix}:",
            "    value: 1",
            f"  field_pdq_is_svpc{suffix}:",
            f"    value: {svpc}",
            f"  field_pdq_suppress_otp{suffix}:",
            f"    value: {suppress_otp}",
            f"  field_pdq_intro_text{suffix}:",
        ]
        if not intro_text:
            lines.append("    value:")
        else:
            lines.append("    value: |")
            lines += intro_text
        lines.append(f"  field_summary_sections{suffix}:")
        for section in values.sections:
            lines += self.__make_section(section)
        return lines

    def __indent(self, value, padding):
        """
        Prefix each line of multiline rich text field with YAML quoting indent

        Each line is stripped of leading and trailing whitespace. Blank lines
        are skipped. Image URLs are temporarily redirected to the legacy site.

        Note: 2019-03-10: image URL munging now taking place upstream.

        Pass:
          value - string with zero or more lines
          padding - string containing spaces for indenting

        Return:
          array of indented strings, one for each line
        """

        if not value:
            return []
        lines = [line.strip() for line in value.splitlines()]
        return [padding + line for line in lines if line]

    def __make_section(self, section):
        """
        Assemble the YAML for a single summary section's ID, title, and HTML

        Pass:
          section - dictionary of the summary section's values

        Return:
          string containing the YAML markup for the summary section's values
        """

        return [
            "    - entity: paragraph",
            "      type: pdq_summary_section",
            "      field_pdq_section_id:",
            f"        value: {section['id']}",
            "      field_pdq_section_title:",
            "        - format: plain_text",
            f"          value: {self.__quote(section['title'])}",
            "      field_pdq_section_html:",
            "        - format: raw_html",
            "          value: |",
        ] + self.__indent(section["html"], self.CIS_HTML_INDENT)

    def __quote(self, me):
        """
        Quote a YAML string value

        Whitespace is normalized so that the value is on a single line

        Pass:
          me - string to be quoted

        Return:
          quoted YAML string
        """

        me = me.strip() if me else ""
        return "'" + sub(r"\s+", " ", me).replace("'", "''") + "'"


parser = ArgumentParser()
parser.add_argument("--type", "-t", required=True, choices=Summary.TYPES)
opts = parser.parse_args()
values = load(stdin)
summary = Summary(values, opts.type)
print(summary.yaml)
