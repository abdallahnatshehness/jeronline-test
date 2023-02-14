#!/usr/bin/env python

"""This file is used to manage versions of automation"""
base_version = '3.11'
versions_dict = {'BDD': '1.0', 'WebTesting': '1.0'}


def get_version(product_name):
    return '%s.%s' % (base_version, versions_dict[product_name])
