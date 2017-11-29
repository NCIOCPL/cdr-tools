<?xml version="1.0"?>
 <xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version="1.0"
                xmlns:cdr="cips.nci.nih.gov/cdr">
<xsl:template match='@*|node()|comment()|processing-instruction()'>
  <xsl:copy>
    <xsl:apply-templates select='@*|node()|comment()|processing-instruction()'/>
  </xsl:copy>
</xsl:template>

<xsl:template match='/GlossaryTermName/TermName/TermNameString'>
  <xsl:choose>
    <xsl:when test='normalize-space(.)!=.'>
      <xsl:element name='TermNameString'>
        <xsl:value-of select='normalize-space(.)'/>
      </xsl:element>
    </xsl:when>
    <xsl:otherwise>
      <xsl:copy-of select='.'/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<xsl:template match='/GlossaryTermName/TranslatedName/TermNameString'>
  <xsl:choose>
    <xsl:when test='normalize-space(.)!=.'>
      <xsl:element name='TermNameString'>
        <xsl:value-of select='normalize-space(.)'/>
      </xsl:element>
    </xsl:when>
    <xsl:otherwise>
      <xsl:copy-of select='.'/>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

</xsl:transform>
