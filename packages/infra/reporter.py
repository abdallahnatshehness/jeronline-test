#!/usr/bin/env python
import atexit
import os
import sys
import copy
import time

import allure
import operator
from threading import Lock
from lxml import etree as ET

from infra import custom_exceptions as ce
from infra import config, logger
from infra.decorators import retry

log = logger.get_logger(__name__)
_lock = Lock()

report_resources_folder = os.path.join(config.utilities_folder, 'report_resources')


def main():
    pass

def get_reporter():
    """A getter function that returns an instance of the main reporter object."""
    return _reporter


class Reporter(object):
    """A class that creates reports using XML, XSLT & HTML"""

    def __init__(self):
        self._xml_root = ET.Element('root')
        self._xml_tree = ET.ElementTree(self._xml_root)
        self._xml_tables = self.add_element('Tables')
        self._xml_headers = self.add_element('Headers')
        self.add_element('Header', root=self._xml_headers, type='full')
        self.add_element('Header', root=self._xml_headers, type='fail')
        self._xml_tables_count = 0
        self._hdlr = None
        self.write_html_prev_time = time.time()


    @property
    def xml_tables_count(self):
        return self._xml_tables_count

    @xml_tables_count.setter
    def xml_tables_count(self, value):
        self._xml_tables_count = value

    def set_hdlr(self, report_folder_path, reporter_name, create_fail_report=False):
        """A setter function that sets a reporter file handler for the main reporter instance."""
        self.create_hdlr(create_fail_report, report_folder_path, reporter_name)
        if create_fail_report:
            self.add_header_rows({'text': 'Failed results', 'href': '%s_fail.html' % reporter_name}, header_type='full')
            self.add_header_rows({'text': 'Full results', 'href': '%s.html' % reporter_name}, header_type='fail')
        self.add_header_rows({'text': 'Parent directory', 'href': '.'})
        if len(sys.argv) > 1:
            self.create_run_command_link(report_folder_path, reporter_name)

    def append_hdlr(self, report_folder_path, reporter_name, create_fail_report=False):
        """Reads a previously created report and appends it to the current report object"""
        self.create_hdlr(create_fail_report, report_folder_path, reporter_name)
        self._xml_tree = self._hdlr.read_xml()
        self._xml_root = self._xml_tree.getroot()
        self._xml_tables = self.get_element('Tables')
        self._xml_headers = self.get_element('Headers')
        self.xml_tables_count = len(self._xml_tables)

    def create_hdlr(self, create_fail_report, report_folder_path, reporter_name):
        self._hdlr = ReporterFileHander(report_folder_path, reporter_name, create_fail_report=create_fail_report)
        atexit.register(self.write_xml)
        atexit.register(lambda: self.write_html(force=True))

    def add_element(self, element_name, root=None, text=None, index=None, **tags):
        """Adds XML element under root (base root or custom root).
           If text is provided, the element text field will be filled.
           If index is not provided, the element will be appended to the end of root, or inserted at supplied index
           Additional tags that are acceptable - bgcolor, href"""

        if root is None:
            root = self._xml_root
        if index is None:
            index = len(root)
        tags = {k: str(v) for k, v in list(tags.items())}
        root.insert(index, ET.Element(element_name, **tags))
        element = root[index]
        if text is not None:
            element.text = str(text)
        if len(log.handlers) > 0:
            log.debug('Adding "%s" element to "%s" (index %s) - %s' % (element_name, root, index, text))
        return element

    def get_element(self, element_type, root=None, element_name='', return_all=False):
        """Returns xml element object from any tree. If more than one element exists, it returns the last one.
           Element type can be: Row, Table, HRow..."""
        if root is None:
            root = self._xml_root
        if element_name != '':
            element_name = "[@name='%s']" % element_name
        elements = root.xpath("%s%s" % (element_type, element_name))
        if return_all:
            return elements
        else:
            try:
                return elements[-1]
            except IndexError:
                raise ce.WEKeyError('%s - %s not found in report' % (element_type, element_name))

    def is_table_exists(self, table_name):
        return len(self.get_table(table_name, return_all=True)) > 0

    def get_table(self, table_name, **kwargs):
        """Returns xml element object from the "Tables" tree. If more than one table exists, it returns the last table"""
        return self.get_element('Table', root=self._xml_tables, element_name=table_name, **kwargs)

    def get_tables(self) -> list:
        """Returns a list of all available tables"""
        return [attrib.attrib.get('name') for attrib in self.get_element('Table', root=self._xml_tables, return_all=True)]

    def get_table_index(self, table_name):
        """Returns index of table (by name)"""
        return self._xml_tables.index(self.get_table(table_name))

    def get_headers(self, header_type='all'):
        """Returns a list from "Headers" node.
           If header_type is "all" then all headers will be returned.
           If a specific header_type is defined it will return a list with the specific header."""

        if header_type == 'all':
            if len(self._xml_headers) == 0:
                raise ce.WEValueError('No headers defined in report')
            return self._xml_headers
        else:
            try:
                return [self._xml_headers.xpath("Header[@type='%s']" % header_type)[0]]
            except IndexError:
                raise ce.WEValueError('Header not defined in report - %s' % header_type)

    def get_xml_columns(self, table_name):
        table = self.get_table(table_name)
        try:
            xml_columns = table.xpath('Columns')[0]
        except IndexError:
            raise ce.WEIndexError('No columns defined in report - %s' % table_name)
        return xml_columns

    def get_columns(self, table_name):
        xml_columns = self.get_xml_columns(table_name)
        return [(col.attrib['name'], col.text) for col in xml_columns]

    def get_columns_info(self, table_name):
        """Returns information about columns in two lists:
           The first list includes all "name" attributes.
           The second list inclues text of all columns."""
        xml_columns = self.get_xml_columns(table_name)
        return [col.attrib['name'] for col in xml_columns], [col.text for col in xml_columns]

    def add_table(self, table_name, **tags):
        """Adds adds an xml element to the "Tables" tree.
           The available tags are "caption" - For adding a caption at the top of the table.
           You can create an iterable table (counting row numbers in first column) by adding a type=iterable tag."""
        if 'type' not in tags:
            tags['type'] = 'basic'
        table = self.add_element('Table', root=self._xml_tables, name=table_name, id=str(self.xml_tables_count), **tags)
        self.xml_tables_count += 1
        self.add_element('Rows', root=table)
        self.add_element('Columns', root=table)
        if self._hdlr is not None:
            self.write_html()
        table_id = self.get_table_tag(table_name, 'id')
        return table, table_id

    def add_table_if_not_exists(self, table_name, *columns):
        if not self.is_table_exists(table_name):
            table, table_id = self.add_table(table_name, caption=table_name)
            self.add_columns(table_name, *columns)
        else:
            table_id = self.get_table_tag(table_name, 'id')
        return table_id

    def get_table_tag(self, table_name, element_name):
        """Return table element or an empty string if not set"""
        return self.get_table(table_name).get(element_name, '')

    def set_table_tags(self, table_name, **tags):
        """Overwrites attributes to a table. Only requested tags will be changed."""
        table = self.get_table(table_name)
        for key, val in list(tags.items()):
            log.debug('Adding tag "%s" to %s - %s' % (val, key, table_name))
            if key == 'href':  # Flipping slashes in href links
                val = val.replace('\\', '/')
            table.set(key, val)
        if self._hdlr is not None:
            self.write_html()

    def set_table_caption(self, table_name, caption):
        """Sets a "caption" attribute to a table in the report"""
        table = self.get_table(table_name)
        log.debug('Setting caption "%s" to table - %s' % (caption, table_name))
        table.set('caption', caption)

    def append_table_caption(self, table_name, caption):
        """Appends to the current table "caption". If a caption is not defined, a new caption will be set."""
        table = self.get_table(table_name)
        cur_caption = table.attrib.get('caption', '')
        new_caption = '%s %s' % (cur_caption, caption)
        log.debug('Setting caption "%s" to table - %s' % (new_caption, table_name))
        table.set('caption', new_caption)

    def get_headers_title(self):
        try:
            return self.get_headers(header_type='full')[0].attrib['title']
        except (IndexError, KeyError, AttributeError) as e:
            raise ce.WERunTimeError('Get title failed - %s' % e)

    def set_headers_title(self, title, header_type='all', add_client_name=True):
        """Sets a "title" attribute to the report headers"""
        if add_client_name:
            title += ' (%s)' % config.client_name
        headers = self.get_headers(header_type=header_type)
        for header in headers:
            log.debug('Setting title "%s" to header - %s' % (title, header))
            if header.get('type', 'full') == 'fail':
                title = 'Failures: ' + title
            header.set('title', title)
        if self._hdlr is not None:
            self.write_html()

    @staticmethod
    def list_to_columns(*l):
        """return a list of tuples to be used with add_columns().
        example: list_to_columns('a d', 'b', 'c') -> [('a_d', 'A D'), ('b', 'B'), ('c', 'C')]"""
        return [(a.replace(' ', '_'), a.title()) for a in l]

    def add_columns(self, table_name, *columns, **kwargs):
        """Adds one or more columns elements to the "Columns".
           If table is an "iterable" type it will add an "iter" column as the first column.
           In case of adding more columns to a table with existing rows,
           the function will add empty values to the new columns in order to draw the table grid

           Optional arguments:
               index - To insert a column (not at the end)"""
        try:
            table = self.get_table(table_name)
        except ce.WEKeyError:
            table = self.add_table(table_name)
        xml_columns = table.xpath('Columns')[0]

        index = kwargs.pop('index', None)
        for i, column in enumerate(columns):
            log.debug('Adding column "%s" to %s' % (column[1], table_name))
            if type(column) not in (list, tuple):
                raise ce.WEValueError('Columns must be tuple or list - %s' % column)
            if column[0][0].isdigit():
                raise ce.WEValueError('column key must not start with a digit - %s' % column[0])
            self.add_element('Column', root=xml_columns, name=column[0], text=column[1], index=index+i if index is not None else None, **kwargs)

        # Adding empty cells to existing rows
        rows = table.xpath('Rows')[0]
        if len(rows) > 0:
            for xml_row in rows:
                for i, col in enumerate(columns):
                    # An empty list with a 0 index is used to trigger IndexError thus inserting None values in the cells
                    self._add_row_cell([], 0, col[0], xml_row, index=index+i if index is not None else None, **kwargs)

        if self._hdlr is not None:
            self.write_html()

    def get_table_rows(self, table_name):
        """Returns a list of rows from a table if found. If no rows are found, it returns an empty list"""
        try:
            return self.get_table(table_name).xpath('Rows')[0]
        except IndexError:
            return []

    def add_row(self, table_name: str, row: (list, tuple), col_index: int=0, row_index: int=None, **tags):
        """Adds a row element to an existing table element.
           Each row is a list with one or multiple items which can be either string or dictionary.
           In case of a dict - each key will define a tag for the row element, and "text" key will be the text of the cell element.
           If table is an "iterable" type it will add the number of rows to the first column.
           This function add also add/modify existing rows by using row and column index.
           Args:
               - table_name - Name of table to add the row
               - row - A list contains row fields to be added
               - col_index - The index of the first column to add. In case of modifying existing rows you can choose which columns to update
               - row_index - The index of a row to modify. If not specified a new row will be added
           Available tags:
            - bgcolor (row and/or cell): To set background color (html color name or code). cell color will override row color.
            - align (row and/or cell): To aligning text in a cell/cells in a row (center / left / right).
            - link (cell only): To create an internal link to an another table using the table's id. Table id can be fetched by calling self.get_table_tag()
            - href (cell only): To create a link. The cell's text will be used as the link's displayed text.
            - image (cell only): To display an image inside the cell. The cell's text will be used as altenative text.
            - type (row only): You can set the type of the row to "fail" so the failures report will be able to filter it.
            - class: 'wrapped-text' (cell only): Option to wrap text, if long string is expected. Cell width changes dynamically based on displayed page width."""

        row = copy.deepcopy(row)
        if type(row) not in (tuple, list):
            raise ce.WETypeError('row must be a list - %s' % row)
        try:
            table = self.get_table(table_name)
        except ce.WEKeyError:
            table = self.add_table(table_name)

        columns, col_text = self.get_columns_info(table_name)
        if len(row) > len(columns):
            raise ce.WEIndexError('%s table - row has more columns than defined in table - (%s)' % (table_name, row))

        rows = table.xpath('Rows')[0]
        if row_index is None:
            xml_row = self.add_element('Row', root=rows, **tags)
            log.debug('Adding row "%s" to - %s' % (row, table_name))
        else:
            xml_row = rows[row_index]
        for i, key in enumerate(columns[col_index:]):
            self._add_row_cell(row, i + col_index, key, xml_row)
        if self._hdlr is not None:
            self.write_html()

    def add_screenshot_to_header(self, screenshot_path=None, screenshot_name='screenshot', msg=''):
        from utils.image_utils import capture_screen
        if not screenshot_path:
            screenshot_path = self.get_html_folderpath()
        screenshot_file = os.path.join(screenshot_path, screenshot_name)
        msg += 'Click here to view screenshot '
        self.add_header_rows({'text': msg, 'href': self.get_relative_path(capture_screen(screenshot_file, dated_file=True))})

    def set_row_values(self, table_name, row, row_index, col_index, **tags):
        """A function that modifies values of an existing row.
           Args:
               - table_name - Name of table to add the row
               - row - A list contains row fields to be added
               - col_index - The index of the first column to modify
               - row_index - The index of a row to modify. If not specified a new row will be added
               - tags - Optional row tags to set"""

        row = copy.deepcopy(row)
        if type(row) not in (tuple, list):
            raise ce.WETypeError('row must be a list - %s' % row)
        table = self.get_table(table_name)

        columns, col_text = self.get_columns_info(table_name)
        if len(row) > len(columns):
            raise ce.WEIndexError('%s table - row has more columns than defined in table - (%s)' % (table_name, row))

        xml_row = self.get_element('Rows', root=table)[row_index]
        for i, key in enumerate(columns[col_index:col_index+len(row)]):
            text, row_tags = self._convert_cell(row, i)
            xml_row[i + col_index].text = text
            for k, v in list(row_tags.items()):
                xml_row[i + col_index].set(k, v)
        for key, val in list(tags.items()):
            log.debug('Adding tag "%s" to %s - %s' % (val, key, xml_row))
            if key == 'href':  # Flipping slashes in href links
                val = val.replace('\\', '/')
            xml_row.set(key, val)
        if self._hdlr is not None:
            self.write_html()

    def _add_row_cell(self, row, i, key, root, index=None):
        """Adding a cell to a row"""
        text, row_tags = self._convert_cell(row, i)
        self.add_element(key, root=root, text=text, index=index, **row_tags)

    def _convert_cell(self, row, i):
        """Converting cell data to text and tags.
           If the requested item is not in the row list, the function returns None.
           This is used when inserting blank or incomplete rows."""
        try:
            cell = row[i]
        except IndexError:
            text = None
            row_tags = {}
        else:
            if type(cell) == dict:
                text = cell.pop('text', None)
                row_tags = cell
            else:
                text = cell
                row_tags = {}
            text = str(text)
        return text, row_tags

    def add_splitter_row(self, table_name, bgcolor='SkyBlue', **tags):
        """Adds a row element with a default bgcolor and the values will be the same as columns"""
        columns, col_text = self.get_columns_info(table_name)
        self.add_row(table_name, col_text, bgcolor=bgcolor, **tags)

    def set_row_tags(self, table_name, row_index, cell_name=None, **tags):
        """Sets attributes either to a row or a cell in a specific table.
           If a cell_name is not set, the attributes will be set to the entire row."""

        table = self.get_table(table_name)
        try:
            row = self.get_element('Rows', root=table)[row_index]
        except IndexError:
            raise ce.WEIndexError('Row %s does not exist in table - %s' % (row_index, table_name))
        if cell_name is None:
            item_to_set = row
        else:
            item_to_set = self.get_element(cell_name, root=row)
        for key, val in list(tags.items()):
            log.debug('Adding tag "%s" to %s - %s' % (val, key, item_to_set))
            if key == 'href':  # Flipping slashes in href links
                val = val.replace('\\', '/')
            item_to_set.set(key, val)
        if self._hdlr is not None:
            self.write_html()

    def add_header_rows(self, *rows, **tags):
        """Adding a header row (or more) to the XML.
           If a header is not defined it will create a new header.
           Available tags:
           - title: Will set the title of the page and will create the main header. This will be defined only if a header is not already defined.
           - href: To create a link. The cell's text will be usded as the link's displayed text.
           - link: To create an internal link to an another table using the table's id. Table id can be fetched by calling self.get_table_tag()
           - image: To display an image inside the cell. The cell's text will be used as altenative text.
           - header_type: "full" to create a row for the full report, "fail" to create a row for the fail report. Default is "all" for both.
           - row_type: "headline" to create a row in the full report, containing given text. in order to place in certain position use 'index' tag."""

        header_type = tags.get('header_type', 'all')
        title = tags.get('title', None)
        headers_list = self.get_headers(header_type=header_type)
        if title is not None:
            self.set_headers_title(title, header_type=header_type)

        for row in rows:
            if type(row) == dict:
                text = row.pop('text', None)
                row_tags = row
            else:
                text = row
                row_tags = {}
            for header in headers_list:
                log.debug('Adding row "%s - %s" to header %s' % (text, row_tags, header))
                self.add_element('HRow', root=header, text=text, **row_tags)
        if self._hdlr is not None:
            self.write_html()

    def sort_rows(self, table_name, *sorting_columns, reverse=False):
        """Sorting rows in a table.
           Arguments:
               table_name: Name of table to sort
               *sorting_columns: A list of indexes referring to columns of which the sorting is done.
               If no sorting columns are defined, the sorting will be done based on all columns in their respective order"""
        table = self.get_table(table_name)
        if len(sorting_columns) == 0:
            sorting_columns = list(range(len(self.get_element('Columns', root=table))))
        elif len(sorting_columns) == 1:
            sorting_columns = (sorting_columns[0], sorting_columns[0])  # Hack: to force the itemgetter to return a tuple
        rows = self.get_element('Rows', root=table)
        # Sort rows in the table by columns, ignoring cells that are None
        rows[:] = sorted(rows, key=lambda x: [(x.text or '') for x in operator.itemgetter(*sorting_columns)(x)], reverse=reverse)
        if self._hdlr is not None:
            self.write_html()

    def get_html_filepath(self, report_name=None):
        """Returns path of html report file if available"""
        try:
            return self._hdlr.get_html_filepath(report_name=report_name)
        except (AttributeError, KeyError) as e:
            raise ce.WEIOError('Report file not defined - %s' % e)

    def get_html_folderpath(self):
        try:
            return self._hdlr.report_folder_path
        except (AttributeError) as e:
            raise ce.WEIOError('Report file not defined - %s' % e)

    def get_relative_path(self, the_path):
        """Returns a relative path to the report folder"""
        from utils import files_utils
        return files_utils.get_relative_path(the_path, self.get_html_folderpath()).replace('\\', '/')

    def write_xml(self, **kwargs):
        """Calls ReporterFileHander.write_xml using self._xml_tree"""
        try:
            self._hdlr.write_xml(self._xml_tree, **kwargs)
        except AttributeError as e:
            raise ce.WEIOError('Report file not defined - %s' % e)

    def write_html(self, force=False, update_rate=0.6, **kwargs):
        elapsed_time = time.time() - self.write_html_prev_time
        if elapsed_time > update_rate or force is True:
            with _lock:
                self.write_html_prev_time = time.time()
            try:
                self._hdlr.write_html(self._xml_tree, **kwargs)
                self.write_html_prev_time = time.time()
            except AttributeError as e:
                raise ce.WEIOError('Report file not defined - %s' % e)
            except IOError as e:
                if force:
                    raise
                log.debug('Failed to write html - %s' % e)

    def get_html(self, table_name, **kwargs):
        html_content = ''
        table_string = f'<!DOCTYPE html><html lang="en">'\
                       '<head>' \
        f'  <title>{table_name}</title>' \
        '  <meta charset="utf-8">' \
        '  <meta name="viewport" content="width=device-width, initial-scale=1">' \
        '  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/css/bootstrap.min.css">' \
        '  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"></script>' \
        '  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/js/bootstrap.min.js"></script>' \
        '</head>' \
                       '<body>'
        try:
            table_index = self.get_table_tag(table_name, 'id')
            html_content = self._hdlr.get_html(self._xml_tree, **kwargs)
            table_string += html_content[html_content.index(f'<table id="tbl-{table_index}">'):]
            table_string = table_string.replace(f'<table id="tbl-{table_index}">',
                                                f'<table id="tbl-{table_index}" class="table table-hover">')
            table_string = table_string[: table_string.index('</table>')+8]
            table_string += '</body></html>'
            table_string = table_string.replace('.wav<', '.wav"/></audio><')
            table_string = table_string.replace('.mp3<', '.mp3"/></audio><')
            table_string = table_string.replace('audiohttps://artifactory.waves.com', '<audio controls><source src="https://artifactory.waves.com')
            table_string = table_string.replace('audiohttp://Automation', '<audio controls><source src="http://Automation')
            table_string = table_string.replace('audiohttp://automation', '<audio controls><source src="http://automation')
            table_string = table_string.replace('audioresources', '<audio controls><source src="resources')
        except Exception as e:
            raise ce.WEIOError(f'Cannot find table {table_name} - {e}')
        return table_string

    def add_table_to_step(self, table_name):
        allure.attach(self.get_html(table_name), table_name, attachment_type=allure.attachment_type.HTML)

    def add_empty_table_to_step(self, table_name):
        allure.attach("", table_name, attachment_type=allure.attachment_type.HTML)

    def add_html_to_step(self):
        
        table_string = f'<!DOCTYPE html><html lang="en">' \
                       '<head>' \
                       f'  <title>file</title>' \
                       '  <meta charset="utf-8">' \
                       '  <meta name="viewport" content="width=device-width, initial-scale=1">' \
                       '  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/css/bootstrap.min.css">' \
                       '  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"></script>' \
                       '  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/js/bootstrap.min.js"></script>' \
                       '</head>' \
                       '<body>'
        table_string += '<a href="./../../IOCancellation.txt">file</a>'
        table_string += '</body></html>'

        allure.attach(table_string, 'file', attachment_type=allure.attachment_type.HTML)

    def add_audio_player_to_step(self, audio_links_dict, audio_names='Audio Files Players'):
        table_string = f'<!DOCTYPE html><html lang="en">' \
                       '<head>' \
                       f'  <title>file</title>' \
                       '  <meta charset="utf-8">' \
                       '  <meta name="viewport" content="width=device-width, initial-scale=1">' \
                       '  <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/css/bootstrap.min.css">' \
                       '  <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"></script>' \
                       '  <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.0/js/bootstrap.min.js"></script>' \
                       '</head>' \
                       '<body>'
        for audio_name, audio_link in audio_links_dict.items():
            audio_link2 = self.get_arti_download_link(audio_link)
            table_string += f'<p>{audio_name}: </p><audio controls><source src="{audio_link2}" /></audio><br/>'
        table_string += '</body></html>'

        allure.attach(table_string, audio_names, attachment_type=allure.attachment_type.HTML)

    def get_audio_player_for_table_cell(self, link):
        if link == '---':
            return link
        if not str(link).startswith('audiohttp'):
            return f'audio{self.get_arti_download_link(link)}'

    def get_arti_download_link(self, arti_link):
        down_art_link = str(arti_link).replace('artifactory.waves.com/artifactory/',
                                              'artifactory.waves.com/ui/api/v1/download?repoKey=').replace(' ',
                                                                                                           '%20')
        down_art_link = down_art_link.replace('artifactory.waves.com/ui/repos/tree/General/', 'artifactory.waves.com/ui/api/v1/download?repoKey=')
        down_art_link = down_art_link.replace('pa-ref-prod-local/', 'pa-ref-prod-local&path=')
        down_art_link = down_art_link.replace('pa-ref-beta-local/', 'pa-ref-beta-local&path=')
        down_art_link = down_art_link.replace('pa-auto-utilities-local/', 'pa-auto-utilities-local&path=')
        return down_art_link

    def add_label_to_step(self, label_name, label_content):
        allure.attach(label_content, label_name, allure.attachment_type.TEXT)

    def add_exception_image_to_step(self, image_path, image_name = 'Exception Screen Shot'):
        allure.attach.file(image_path, image_name, attachment_type=allure.attachment_type.JPG)

    def add_images_to_step(self, images):
        for image_path, image_name in images:
            self.add_image_to_step(image_path, image_name)

    def add_image_to_step(self, image_path, image_name = 'Screen Shot'):
        allure.attach.file(image_path, image_name, attachment_type=allure.attachment_type.PNG)

    def add_text_file_to_step(self, image_path, image_name = 'Attached file'):
        allure.attach.file(image_path, image_name, attachment_type=allure.attachment_type.TEXT)

    def add_zip_file_to_step(self, zip_path, zip_name='Attached file'):
        allure.attach.file(zip_path, zip_name, attachment_type="application/zip", extension='zip')

    def add_wav_file_to_step(self, audio_file, audio_name = 'Attached file'):
        allure.attach.file(audio_file, audio_name, attachment_type="audio/wav", extension='wav')

    def add_json_file_to_step(self, image_path, image_name = 'Attached file'):
        allure.attach.file(image_path, image_name, attachment_type="application/json", extension='txt')

    def add_txt_file_as_link_to_step(self, image_path, image_name = 'Attached file'):
        allure.attach.file(image_path, image_name, attachment_type="text/x-json", extension='txt')

    def add_excel_file_as_link_to_step(self, image_path, file_name = 'Attached file'):
        allure.attach.file(image_path, file_name, attachment_type="application/vnd.ms-excel", extension='csv')

    def add_txt_file_content_to_step(self, image_path, image_name = 'Attached file'):
        allure.attach.file(image_path, image_name, attachment_type="text/plain", extension='txt')

    def add_link_to_step(self, file_path, lable_name='Screen Shot', file_type=allure.attachment_type.PNG):
        allure.attach(file_path, lable_name, file_type)

    def add_img_from_arti_link_to_step(self, image_name='Image', image_link='Screen Shot'):
        image_download_link = self.get_arti_download_link(image_link)
        img_html = f"""
        <!DOCTYPE html>
        <html>
        <body>
            <a href='{image_link}' target="_blank">
            <img src='{image_download_link}'
            title='Click to open in Artifactory'>
            </a>
        </body>
        </html>
        """
        allure.attach(img_html, image_name, attachment_type=allure.attachment_type.HTML)

    def add_slideshow_img_from_arti_links_to_step(self, images_dict, slide_show_desc='Slide Show'):
        total_slide = len(images_dict)

        test = '''
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        * {box-sizing: border-box}
        body {font-family: Verdana, sans-serif; margin:0}
        .mySlides {display: none}
        img {vertical-align: middle;}

        /* Slideshow container */
        .slideshow-container {
          max-width: 1000px;
          position: relative;
          margin: auto;
        }

        /* Next & previous buttons */
        .prev, .next {
          cursor: pointer;
          position: absolute;
          top: 50%;
          width: auto;
          padding: 16px;
          margin-top: -22px;
          color: white;
          font-weight: bold;
          font-size: 18px;
          transition: 0.6s ease;
          border-radius: 0 3px 3px 0;
          user-select: none;
        }

        /* Position the "next button" to the right */
        .next {
          right: 0;
          border-radius: 3px 0 0 3px;
        }

        /* On hover, add a black background color with a little bit see-through */
        .prev:hover, .next:hover {
          background-color: rgba(0,0,0,0.8);
        }

        /* Caption text */
        .text {
          color: green;
          font-size: 15px;
          padding: 8px 12px;
          bottom: 8px;
          width: 100%;
          text-align: center;
        }

        /* Number text (1/3 etc) */
        .numbertext {
          color: green;
          font-size: 12px;
          padding: 8px 12px;
          position: absolute;
          top: 0;
        }

        /* The dots/bullets/indicators */
        .dot {
          cursor: pointer;
          height: 15px;
          width: 15px;
          margin: 0 2px;
          background-color: #bbb;
          border-radius: 50%;
          display: inline-block;
          transition: background-color 0.6s ease;
        }

        .active, .dot:hover {
          background-color: #717171;
        }

        /* Fading animation */
        .fade {
          animation-name: fade;
          animation-duration: 1.5s;
        }

        @keyframes fade {
          from {opacity: .4} 
          to {opacity: 1}
        }

        /* On smaller screens, decrease text size */
        @media only screen and (max-width: 300px) {
          .prev, .next,.text {font-size: 11px}
        }
        </style>
        </head>
        <body style="height:100%">

        <div class="slideshow-container">'''

        i = 1
        for image_name, image_link in images_dict.items():
            image_link_edited = self.get_arti_download_link(image_link)
            test += '''   <div class="mySlides fade">'''
            test += f'''   <div class="text">{image_name}</div>'''
            test += f'''  <div class="numbertext">{i} / {total_slide}</div>'''
            test += f'''  <img src="{image_link_edited}" style="width:100%">'''
            test += f'''
                    </div>'''
            i += 1

        test +='''<a class="prev" onclick="plusSlides(-1)">PREV</a>
        <a class="next" onclick="plusSlides(1)">NEXT</a>

        </div>
        <br>

        <div style="text-align:center">'''
        for j in range(total_slide):
            test += f'''<span class="dot" onclick="currentSlide({j+1})"></span>'''
        test += '''</div>

        <script>
        let slideIndex = 1;
        showSlides(slideIndex);

        function plusSlides(n) {
          showSlides(slideIndex += n);
        }

        function currentSlide(n) {
          showSlides(slideIndex = n);
        }

        function showSlides(n) {
          let i;
          let slides = document.getElementsByClassName("mySlides");
          let dots = document.getElementsByClassName("dot");
          if (n > slides.length) {slideIndex = 1}    
          if (n < 1) {slideIndex = slides.length}
          for (i = 0; i < slides.length; i++) {
            slides[i].style.display = "none";  
          }
          for (i = 0; i < dots.length; i++) {
            dots[i].className = dots[i].className.replace(" active", "");
          }
          slides[slideIndex-1].style.display = "block";  
          dots[slideIndex-1].className += " active";
        }
        </script>

        </body>
        </html> 
        '''
        allure.attach(test, slide_show_desc, attachment_type=allure.attachment_type.HTML)

    def add_jira_issue_link_to_step(self, issue_links_dict, label='Jira issues'):
        link_template = '<a href="LINK_URL_PLACEHOLDER" target="_blank" title="LINK_HINT_PLACEHOLDER">LINK_NAME_PLACEHOLDER</a>'
        ll = ''
        for link_name, [link_url, link_summary] in issue_links_dict.items():
            ll += link_template.replace('LINK_URL_PLACEHOLDER', link_url).replace('LINK_NAME_PLACEHOLDER', link_name).replace("LINK_HINT_PLACEHOLDER", link_summary) +', '
        links_html = f'<!DOCTYPE html style="height:50px"><html style="height:50px"><body>{ll[:-2]}</body></html>'
        allure.attach(links_html, label, attachment_type=allure.attachment_type.HTML)

    def add_links_to_step(self, links_dict, label='Links'):
        link_template = '<a href="LINK_URL_PLACEHOLDER" target="_blank">LINK_NAME_PLACEHOLDER</a>'
        ll = ''
        for link_name, link_url in links_dict.items():
            ll += link_template.replace('LINK_URL_PLACEHOLDER', link_url).replace('LINK_NAME_PLACEHOLDER', link_name) +', '
        links_html = f'<!DOCTYPE html style="height:50px"><html style="height:50px"><body>{ll[:-2]}</body></html>'
        allure.attach(links_html, label, attachment_type=allure.attachment_type.HTML)


    def create_run_command_link(self, report_folder_path, reporter_name):
        """Add a link on report to command with arguments"""
        argv = list(sys.argv)
        py_file = argv.pop(0)
        if '--bdd_args' in argv: #wrap the bdd args in double quote
            argv[argv.index('--bdd_args') + 1] = f'\"{argv[argv.index("--bdd_args") + 1]}\"'
        run_command_file = os.path.join(report_folder_path, reporter_name + '_command.txt')
        self.add_header_rows({'text': 'Run command', 'href': self.get_relative_path(run_command_file)})
        with open(run_command_file, 'w') as stream:
            stream.write(py_file + '\n')
            stream.write(' '.join(argv))

    def get_table_rows_info(self, table_name):
        all_rows_info = []
        rows = [row.findall('*') for row in self.get_table_rows(table_name)]
        for row in rows:
            row_info = []
            for row_element in row:
                row_info.append((row_element.tag, row_element.text))
            all_rows_info.append(row_info)
        return all_rows_info


class ReporterFileHander(object):
    """A helper class that sets up report files - xml, xslt, html"""
    def __init__(self, report_folder_path, report_name, create_fail_report=False):
        self.report_folder_path = report_folder_path
        os.makedirs(os.path.join(self.report_folder_path, 'resources'), exist_ok=True)
        self.report_name = report_name
        self.create_fail_report = create_fail_report
        self.xml_report_file = os.path.join(self.report_folder_path, 'resources', self.report_name + '.xml')
        self.html_report_files = dict()
        self.xslt_trees = dict()
        self.create_resource_files()
        if self.create_fail_report:
            self.create_resource_files(template_name='report_fail_template', resource_name='%s_fail' % self.report_name)

    def get_html_filepath(self, report_name=None):
        """Returns path of html report file"""
        if report_name is None:
            report_name = self.report_name
        return self.html_report_files[report_name]

    @retry(2, exceptions=(OSError, ), delay=10)
    def read_xml(self):
        """Reads xml file and returns an xml tree"""
        xml_tree = ET.parse(self.xml_report_file, parser=ET.XMLParser(remove_blank_text=True))
        return xml_tree

    @retry(2, exceptions=(OSError, FileNotFoundError), delay=10)
    def write_xml(self, xml_tree, xml_file=None, pretty_print=True):
        """Writes xml data to file"""
        if xml_file is None:
            xml_file = self.xml_report_file
        log.debug('Writing report to XML - %s' % xml_file)
        os.makedirs(os.path.dirname(xml_file), exist_ok=True)
        xml_tree.write(xml_file, xml_declaration=True, encoding='utf-16', pretty_print=pretty_print)

    def write_html(self, xml_tree):
        """Writes an html file using xslt tree"""
        for resource_name in self.html_report_files:
            transform_root = ET.XSLT(self.xslt_trees[resource_name])(xml_tree)
            html_file = self.html_report_files[resource_name]
            os.makedirs(os.path.dirname(html_file), exist_ok=True)
            with open(html_file, 'w') as stream:
                stream.write(ET.tostring(transform_root, encoding='unicode', method='html', pretty_print=True))

    def get_html(self, xml_tree):
        """Get an html file using xslt tree"""
        for resource_name in self.html_report_files:
            transform_root = ET.XSLT(self.xslt_trees[resource_name])(xml_tree)
            html_file = self.html_report_files[resource_name]
            os.makedirs(os.path.dirname(html_file), exist_ok=True)
            a = ''
            with open(html_file, 'w') as stream:
                a += ET.tostring(transform_root, encoding='unicode', method='html', pretty_print=True)
            return a

    def create_resource_files(self, template_name='report_template', resource_name=None):
        """Copies xsl and html files from report_resources folder to the report folder.
        It also renames the filenames inside the html file."""
        if resource_name is None:
            resource_name = self.report_name
        self.xslt_trees[resource_name] = ET.parse(os.path.join(report_resources_folder, template_name + '.xsl'))
        self.html_report_files[resource_name] = os.path.join(self.report_folder_path, resource_name + '.html')


_reporter = Reporter()


if __name__ == '__main__':
    main()
