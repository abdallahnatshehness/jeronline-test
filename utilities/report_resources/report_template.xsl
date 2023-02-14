<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0">
	<xsl:output method="html"/>
		<xsl:template match="/*">
			<html>
				<style>
					table, th, td { border: 1px solid black; }
					td, th { padding: 7px; white-space: pre; }
                    td.wrapped-text { padding: 7px; white-space: normal; }
					table { border-collapse: collapse; margin: 20px; }
					caption { font-weight: bold; padding: 10px; font-size: 20px; white-space: pre; }
					h1 { padding: 10px; text-align: center; margin-bottom: -10px; white-space: pre; }
					p { font-size: 18; margin-left: 20px; margin-bottom: 0; margin-top: 0; white-space: pre; }
					dd, dt { margin-left: 20px; white-space: pre; }
				</style>
				<head>
					<xsl:apply-templates select="Headers/Header[@type = 'full']"/>
				</head>
				<body>
					<xsl:apply-templates select="Tables/Table"/>
				</body>
			</html>
		</xsl:template>

		<xsl:template match="Header">
			<title><xsl:value-of select="@title"/></title>
			<h1><xsl:value-of select="@title"/></h1>
			<DL><xsl:apply-templates select="HRow"/></DL>
		</xsl:template>

	<xsl:template match="HRow">
		<DD>
			<xsl:choose>
				<xsl:when test="@href">
					<a>
						<xsl:attribute name="href"><xsl:value-of select="@href"/></xsl:attribute>
						<xsl:value-of select="text()"/>
					</a>
				</xsl:when>
				<xsl:when test="@link">
					<a>
						<xsl:attribute name="href">#tbl-<xsl:value-of select="@link"/></xsl:attribute>
						<xsl:value-of select="text()"/>
					</a>
				</xsl:when>
				<xsl:when test="@row_type='headline'">
					<a>
						<p align="center">
							<font size='6'><xsl:value-of select="text()"/></font>
						</p>
					</a>
				</xsl:when>
                <xsl:when test="@row_type='boldline'">
					<a>
                        <font size='4'><b><xsl:value-of select="text()"/></b></font>
					</a>
				</xsl:when>
                <xsl:when test="@row_type='step_pass'">
                    <xsl:value-of select="text()"/><font color='green'> - PASS!</font>
				</xsl:when>
                <xsl:when test="@row_type='step_fail'">
                    <xsl:value-of select="text()"/><font color='red'> - FAIL!</font>
				</xsl:when>
				<xsl:when test="@image">
					<img>
						<xsl:attribute name="alt"><xsl:value-of select="text()"/></xsl:attribute>
						<xsl:attribute name="src"><xsl:value-of select="@image"/></xsl:attribute>
					</img>
				</xsl:when>
				<xsl:otherwise>
					<xsl:value-of select="text()"/>
				</xsl:otherwise>
			</xsl:choose>
		</DD>
	</xsl:template>

	<xsl:template match="Table">
		<xsl:if test="count(Rows/Row) != 0">
			<table>
				<xsl:attribute name="id">tbl-<xsl:value-of select="@id"/></xsl:attribute>
				<caption><xsl:value-of select="@caption"/></caption>
				<tr bgcolor="SkyBlue">
					<xsl:if test="@type='iterable'"><th>#</th></xsl:if>
					<xsl:apply-templates select="Columns/*"/>
				</tr>
				<xsl:apply-templates select="Rows/Row"/>
			</table>
		</xsl:if>
	</xsl:template>

	<xsl:template match="Column[not(@hidden = 'true')]">
        <th><xsl:value-of select="text()"/></th>
	</xsl:template>

	<xsl:template match="Row">
	<tr>
		<xsl:if test="../../@type='iterable'">
			<td>
				<xsl:attribute name="bgcolor"><xsl:value-of select="@bgcolor"/></xsl:attribute>
				<xsl:value-of select="position()"/>
			</td>
		</xsl:if>
		<xsl:for-each select="./*">
			<td>
                <xsl:attribute name="class"><xsl:value-of select="@class"/></xsl:attribute>
				<xsl:choose>
					<xsl:when test="@bgcolor">
						 <xsl:attribute name="bgcolor"><xsl:value-of select="@bgcolor"/></xsl:attribute>
					</xsl:when>
					<xsl:otherwise>
						 <xsl:attribute name="bgcolor"><xsl:value-of select="../@bgcolor"/></xsl:attribute>
					</xsl:otherwise>
				</xsl:choose>
				<xsl:choose>
					<xsl:when test="@align">
						<xsl:attribute name="align"><xsl:value-of select="@align"/></xsl:attribute>
					</xsl:when>
					<xsl:otherwise>
						<xsl:attribute name="align"><xsl:value-of select="../@align"/></xsl:attribute>
					</xsl:otherwise>
				</xsl:choose>
				<xsl:choose>
					<xsl:when test="@link">
						<a>
							<xsl:attribute name="href">#tbl-<xsl:value-of select="@link"/></xsl:attribute>
							<xsl:value-of select="text()"/>
						</a>
					</xsl:when>
					<xsl:when test="@href">
						<a>
							<xsl:attribute name="href"><xsl:value-of select="@href"/></xsl:attribute>
							<xsl:value-of select="text()"/>
						</a>
					</xsl:when>
					<xsl:when test="@image">
						<img>
							<xsl:attribute name="alt"><xsl:value-of select="text()"/></xsl:attribute>
							<xsl:attribute name="src"><xsl:value-of select="@image"/></xsl:attribute>
						</img>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="text()"/>
					</xsl:otherwise>
				</xsl:choose>
			</td>
		</xsl:for-each>
	</tr>
	</xsl:template>
</xsl:stylesheet>
